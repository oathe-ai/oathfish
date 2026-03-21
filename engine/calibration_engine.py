"""Calibration engine for the OathFish swarm intelligence system.

Provides 5 MCP tools for tracking predictions, recording outcomes,
computing domain/archetype bias, and reporting ensemble metrics.
All computations are deterministic -- no LLM in the correction loop (C-B05).

Correction schedule (from research consensus):
- Runs 1-2: RECORD_ONLY -- accumulate data, no corrections
- Runs 3-9: DOMAIN_ADDITIVE -- apply alpha_d where |MSE|>0.10 AND n>=15
- Runs 10-49: ARCHETYPE_ADDITIVE -- extend to archetype level where n>=5
- Runs 50+: LOGISTIC -- logistic recalibration where n>=50/domain
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from engine.calibration_models import (
    CalibrationPrediction,
    CalibrationOutcome,
    DomainBias,
    ArchetypeBias,
    EnsembleMetrics,
    PredictionDomain,
    QuestionComplexity,
)
from engine.domain_classifier import (
    classify_domain,
    classify_horizon,
    classify_complexity,
    compute_holdout_flag,
    generate_prediction_id,
    load_taxonomy,
)

UTC = timezone.utc


class CalibrationEngine:
    """Deterministic calibration engine. All computations are pure functions
    of the stored prediction/outcome data. No LLM in the correction loop."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.calibration_dir = data_dir / "calibration"
        self.calibration_dir.mkdir(parents=True, exist_ok=True)
        self.predictions_file = self.calibration_dir / "predictions.json"
        self.outcomes_file = self.calibration_dir / "outcomes.json"
        self.corrections_file = self.calibration_dir / "domain_corrections.json"
        self.taxonomy = load_taxonomy(
            data_dir / "config" / "domain_taxonomy.json"
        )
        self._predictions: list = self._load_json(self.predictions_file)
        self._outcomes: list = self._load_json(self.outcomes_file)

    def _load_json(self, path: Path) -> list:
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []

    def _save_predictions(self) -> None:
        with open(self.predictions_file, "w") as f:
            json.dump(self._predictions, f, indent=2, default=str)

    def _save_outcomes(self) -> None:
        with open(self.outcomes_file, "w") as f:
            json.dump(self._outcomes, f, indent=2, default=str)

    # -- Tool 1: calibration_record_prediction --

    def record_prediction(
        self,
        run_id: str,
        archetype_id: str,
        question_id: str,
        question_text: str,
        forecast_probability: float,
        confidence: float,
        base_rate_anchor: str,
        timeframe: str,
        is_baseline: bool = False,
        is_bootstrap: bool = False,
    ) -> CalibrationPrediction:
        """Records a structured prediction for future outcome comparison.
        Auto-classifies domain, horizon, complexity. Assigns holdout flag.
        Persists immediately to disk (write-through, C-23)."""

        prediction_id = generate_prediction_id(run_id, archetype_id, question_id)
        domain = classify_domain(question_text, self.taxonomy)
        horizon = classify_horizon(timeframe)
        complexity = classify_complexity(question_text)
        is_holdout = compute_holdout_flag(prediction_id)

        prediction = CalibrationPrediction(
            prediction_id=prediction_id,
            run_id=run_id,
            archetype_id=archetype_id,
            question_id=question_id,
            question_text=question_text,
            domain=domain,
            horizon=horizon,
            complexity=complexity,
            forecast_probability=forecast_probability,
            confidence=confidence,
            base_rate_anchor=base_rate_anchor,
            is_baseline=is_baseline,
            is_bootstrap=is_bootstrap,
            is_holdout=is_holdout,
            created_at=datetime.now(UTC),
        )

        self._predictions.append(prediction.model_dump(mode="json"))
        self._save_predictions()
        return prediction

    # -- Tool 2: calibration_record_outcome --

    def record_outcome(
        self,
        question_id: str,
        run_id: str,
        actual_outcome: bool,
        resolution_source: str,
    ) -> dict:
        """Records the actual outcome and triggers Brier score computation
        for all predictions matching this question_id."""

        outcome = CalibrationOutcome(
            question_id=question_id,
            run_id=run_id,
            actual_outcome=actual_outcome,
            resolution_date=datetime.now(UTC),
            resolution_source=resolution_source,
            resolved_at=datetime.now(UTC),
        )

        self._outcomes.append(outcome.model_dump(mode="json"))
        self._save_outcomes()

        # Compute Brier scores for all matching predictions
        updated_count = 0
        outcome_val = 1.0 if actual_outcome else 0.0

        for pred in self._predictions:
            if pred["question_id"] == question_id and not pred["resolved"]:
                f = pred["forecast_probability"]
                pred["resolved"] = True
                pred["outcome"] = actual_outcome
                pred["brier_score"] = (f - outcome_val) ** 2
                updated_count += 1

        self._save_predictions()
        self.write_domain_corrections()

        return {
            "question_id": question_id,
            "actual_outcome": actual_outcome,
            "predictions_updated": updated_count,
            "resolution_source": resolution_source,
        }

    # -- Tool 3: calibration_get_domain_bias --

    def get_domain_bias(
        self,
        domain: str,
        min_n: int = 3,
        exclude_holdout: bool = True,
        exclude_baseline: bool = True,
        exclude_bootstrap: bool = False,
    ) -> Optional[DomainBias]:
        """Returns mean signed error for a domain.
        Positive MSE = ensemble predicts too high (overconfident/acquiescent).

        Statistical test: one-sample t-test of (f_i - o_i) against 0.
        NOTE (SK-03 fix): Uses t-distribution, not normal CDF."""

        errors = []
        forecasts = []
        outcomes_count = {"positive": 0, "total": 0}

        for pred in self._predictions:
            if not pred["resolved"]:
                continue
            if pred["domain"] != domain:
                continue
            if exclude_holdout and pred["is_holdout"]:
                continue
            if exclude_baseline and pred["is_baseline"]:
                continue
            if exclude_bootstrap and pred["is_bootstrap"]:
                continue

            f = pred["forecast_probability"]
            o = 1.0 if pred["outcome"] else 0.0
            errors.append(f - o)
            forecasts.append(f)
            outcomes_count["total"] += 1
            if pred["outcome"]:
                outcomes_count["positive"] += 1

        n = len(errors)
        if n < min_n:
            return None

        mse = sum(errors) / n
        if n > 1:
            variance = sum((e - mse) ** 2 for e in errors) / (n - 1)
            sd = math.sqrt(variance)
            se = sd / math.sqrt(n)
            t_stat = mse / se if se > 0 else 0.0
            # Two-sided p-value from t-distribution (SK-03 fix)
            p_value = 2 * _t_sf(abs(t_stat), n - 1)
        else:
            sd = 0.0
            t_stat = 0.0
            p_value = 1.0

        # Determine correction activation (tiered thresholds, SK-02)
        total_runs = len(set(p["run_id"] for p in self._predictions))
        correction_active = False
        correction_value = 0.0

        if total_runs >= 18 and n >= 90 and p_value < 0.10:
            correction_active = True
            correction_value = mse
        elif total_runs >= 10 and n >= 45 and abs(mse) > 0.05:
            correction_active = True
            correction_value = mse
        elif total_runs >= 3 and n >= 15 and abs(mse) > 0.10:
            correction_active = True
            correction_value = mse

        acq_rate = sum(forecasts) / len(forecasts) if forecasts else 0.5
        base_rate = (outcomes_count["positive"] / outcomes_count["total"]
                     if outcomes_count["total"] > 0 else 0.5)

        return DomainBias(
            domain=PredictionDomain(domain),
            mean_signed_error=round(mse, 6),
            standard_deviation=round(sd, 6),
            n_observations=n,
            t_statistic=round(t_stat, 4),
            p_value=round(p_value, 6),
            correction_active=correction_active,
            correction_value=round(correction_value, 6),
            acquiescence_rate=round(acq_rate, 4),
            base_rate=round(base_rate, 4),
        )

    # -- Tool 4: calibration_get_archetype_bias --

    def get_archetype_bias(
        self,
        archetype_id: str,
        domain: Optional[str] = None,
        min_n: int = 5,
        exclude_holdout: bool = True,
    ) -> Optional[ArchetypeBias]:
        """Returns per-archetype directional bias.
        Optionally filtered by domain."""

        errors = []
        brier_scores = []
        forecasts = []

        for pred in self._predictions:
            if not pred["resolved"]:
                continue
            if pred["archetype_id"] != archetype_id:
                continue
            if domain and pred["domain"] != domain:
                continue
            if exclude_holdout and pred["is_holdout"]:
                continue
            if pred["is_baseline"]:
                continue

            f = pred["forecast_probability"]
            o = 1.0 if pred["outcome"] else 0.0
            errors.append(f - o)
            brier_scores.append((f - o) ** 2)
            forecasts.append(f)

        n = len(errors)
        if n < min_n:
            return None

        mse = sum(errors) / n
        brier = sum(brier_scores) / n
        acq_rate = sum(forecasts) / len(forecasts) if forecasts else 0.5

        return ArchetypeBias(
            archetype_id=archetype_id,
            domain=PredictionDomain(domain) if domain else None,
            mean_signed_error=round(mse, 6),
            n_observations=n,
            brier_score=round(brier, 6),
            acquiescence_rate=round(acq_rate, 4),
        )

    # -- Tool 5: calibration_get_ensemble_metrics --

    def get_ensemble_metrics(
        self,
        window: int = 10,
    ) -> EnsembleMetrics:
        """Returns overall ensemble calibration metrics.
        Compares corrected vs uncorrected, baseline vs informed,
        training vs holdout.

        Delta sign convention (unified, SK-05 fix): POSITIVE = IMPROVEMENT."""

        # Get all resolved non-baseline, non-bootstrap predictions
        resolved = [p for p in self._predictions
                    if p["resolved"] and not p["is_baseline"]
                    and not p["is_bootstrap"]]

        # Limit to window of most recent runs
        all_runs = sorted(set(p["run_id"] for p in self._predictions))
        window_runs = all_runs[-window:] if len(all_runs) > window else all_runs
        resolved = [p for p in resolved if p["run_id"] in window_runs]

        n_total = len(self._predictions)
        n_resolved = len(resolved)

        if n_resolved == 0:
            return self._empty_ensemble_metrics(n_total, len(window_runs))

        # Compute domain corrections
        corrections = {}
        for domain in PredictionDomain:
            if domain == PredictionDomain.UNCLASSIFIED:
                continue
            bias = self.get_domain_bias(domain.value, min_n=3)
            if bias and bias.correction_active:
                corrections[domain.value] = bias.correction_value

        # Split training vs holdout
        training = [p for p in resolved if not p["is_holdout"]]
        holdout = [p for p in resolved if p["is_holdout"]]

        # Raw Brier (all resolved, no corrections)
        brier_raw = self._compute_brier(resolved)

        # Corrected Brier (apply domain corrections)
        brier_corrected = self._compute_brier_corrected(resolved, corrections)

        # Baseline Brier (pre-deliberation predictions)
        baseline_preds = [p for p in self._predictions
                         if p["resolved"] and p["is_baseline"]
                         and p["run_id"] in window_runs]
        brier_baseline = self._compute_brier(baseline_preds) if baseline_preds else None

        # Informed Brier (post-deliberation, non-baseline)
        brier_informed = brier_raw

        # Deliberation delta (positive = deliberation helps)
        deliberation_delta = None
        if brier_baseline is not None:
            deliberation_delta = round(brier_baseline - brier_raw, 6)

        # Holdout vs training
        brier_holdout = self._compute_brier(holdout) if holdout else None
        brier_training = self._compute_brier(training) if training else None

        overfitting_gap = None
        overfitting_detected = False
        if brier_holdout is not None and brier_training is not None:
            overfitting_gap = round(brier_holdout - brier_training, 6)
            overfitting_detected = overfitting_gap > 0.02

        # Acquiescence rate
        all_forecasts = [p["forecast_probability"] for p in resolved]
        acq_rate = sum(all_forecasts) / len(all_forecasts) if all_forecasts else 0.5

        # Correction schedule stage
        total_runs = len(all_runs)
        if total_runs < 3:
            stage = "RECORD_ONLY"
        elif total_runs < 10:
            stage = "DOMAIN_ADDITIVE"
        elif total_runs < 50:
            stage = "ARCHETYPE_ADDITIVE"
        else:
            stage = "LOGISTIC"

        # Domain bias summaries
        domain_biases = []
        for domain in PredictionDomain:
            if domain == PredictionDomain.UNCLASSIFIED:
                continue
            bias = self.get_domain_bias(domain.value, min_n=1)
            if bias:
                domain_biases.append(bias)

        self.write_domain_corrections()

        return EnsembleMetrics(
            brier_raw=round(brier_raw, 6),
            brier_corrected=round(brier_corrected, 6),
            brier_gap=round(brier_raw - brier_corrected, 6),
            brier_baseline=round(brier_baseline, 6) if brier_baseline is not None else None,
            brier_informed=round(brier_informed, 6) if brier_informed is not None else None,
            deliberation_delta=deliberation_delta,
            acquiescence_rate=round(acq_rate, 4),
            n_predictions=n_total,
            n_resolved=n_resolved,
            n_holdout=len(holdout),
            brier_holdout=round(brier_holdout, 6) if brier_holdout is not None else None,
            brier_training=round(brier_training, 6) if brier_training is not None else None,
            overfitting_gap=overfitting_gap,
            overfitting_detected=overfitting_detected,
            domain_biases=domain_biases,
            correction_schedule_stage=stage,
            window_runs=len(window_runs),
        )

    # -- Stratified A/B comparison --

    def get_deliberation_comparison(
        self,
        window: int = 10,
    ) -> dict:
        """Stratified A/B comparison of baseline vs deliberation-informed predictions."""
        all_runs = sorted(set(p["run_id"] for p in self._predictions))
        window_runs = all_runs[-window:] if len(all_runs) > window else all_runs

        strata = {}
        for complexity in QuestionComplexity:
            baseline = [p for p in self._predictions
                        if p["resolved"] and p["is_baseline"]
                        and p["complexity"] == complexity.value
                        and p["run_id"] in window_runs]
            informed = [p for p in self._predictions
                        if p["resolved"] and not p["is_baseline"]
                        and not p["is_bootstrap"]
                        and p["complexity"] == complexity.value
                        and p["run_id"] in window_runs]

            brier_b = self._compute_brier(baseline) if baseline else None
            brier_i = self._compute_brier(informed) if informed else None
            delta = round(brier_b - brier_i, 6) if brier_b is not None and brier_i is not None else None

            strata[complexity.value] = {
                "n_baseline": len(baseline),
                "n_informed": len(informed),
                "brier_baseline": round(brier_b, 6) if brier_b is not None else None,
                "brier_informed": round(brier_i, 6) if brier_i is not None else None,
                "deliberation_delta": delta,
                "deliberation_helps": delta > 0 if delta is not None else None,
            }

        return {
            "strata": strata,
            "recommendation": self._ab_recommendation(strata),
        }

    def _ab_recommendation(self, strata: dict) -> str:
        multi = strata.get("MULTI_FACTOR", {})
        simple = strata.get("SIMPLE_BINARY", {})

        if multi.get("deliberation_delta") is not None and multi["deliberation_delta"] > 0.01:
            if simple.get("deliberation_delta") is not None and simple["deliberation_delta"] < -0.01:
                return "DELIBERATION_HELPS_MULTI_FACTOR_ONLY: Skip deliberation on simple binary questions."
            return "DELIBERATION_HELPS_BOTH: Continue full pipeline."

        if multi.get("deliberation_delta") is not None and multi["deliberation_delta"] < -0.01:
            return "DELIBERATION_HURTS: Consider simplifying to baseline-only architecture."

        return "INSUFFICIENT_DATA: More runs needed for reliable comparison."

    # -- Cross-engine interface --

    def write_domain_corrections(self) -> None:
        """Write domain_corrections.json for Worker A's amplify_aggregate().

        Schema:
        {
          "corrections": {
            "DOMAIN": {"offset": float, "n": int, "direction": "over"|"under",
                        "p_value": float, "correction_active": bool}
          },
          "last_updated": ISO datetime,
          "correction_schedule_stage": str
        }
        """
        corrections = {}
        for domain in PredictionDomain:
            if domain == PredictionDomain.UNCLASSIFIED:
                continue
            bias = self.get_domain_bias(domain.value, min_n=3)
            if bias:
                corrections[domain.value] = {
                    "offset": round(bias.correction_value, 6),
                    "n": bias.n_observations,
                    "direction": "over" if bias.correction_value > 0 else "under",
                    "p_value": bias.p_value,
                    "correction_active": bias.correction_active,
                }

        total_runs = len(set(p["run_id"] for p in self._predictions))
        if total_runs < 3:
            stage = "RECORD_ONLY"
        elif total_runs < 10:
            stage = "DOMAIN_ADDITIVE"
        elif total_runs < 50:
            stage = "ARCHETYPE_ADDITIVE"
        else:
            stage = "LOGISTIC"

        output = {
            "corrections": corrections,
            "last_updated": datetime.now(UTC).isoformat(),
            "correction_schedule_stage": stage,
        }

        with open(self.corrections_file, "w") as f:
            json.dump(output, f, indent=2)

    # -- Internal helpers --

    def _compute_brier(self, predictions: list) -> float:
        """BS = (1/N) * SUM((f_i - o_i)^2)"""
        if not predictions:
            return 0.0
        total = 0.0
        for p in predictions:
            f = p["forecast_probability"]
            o = 1.0 if p["outcome"] else 0.0
            total += (f - o) ** 2
        return total / len(predictions)

    def _compute_brier_corrected(
        self,
        predictions: list,
        corrections: dict,
    ) -> float:
        """BS_corrected = (1/N) * SUM((clamp(f_i - alpha_d, 0, 1) - o_i)^2)"""
        if not predictions:
            return 0.0
        total = 0.0
        for p in predictions:
            f = p["forecast_probability"]
            domain = p["domain"]
            alpha = corrections.get(domain, 0.0)
            f_corrected = max(0.0, min(1.0, f - alpha))
            o = 1.0 if p["outcome"] else 0.0
            total += (f_corrected - o) ** 2
        return total / len(predictions)

    def apply_correction(
        self,
        forecast: float,
        domain: str,
    ) -> tuple:
        """Apply domain correction to a single forecast.
        Returns (corrected_forecast, correction_applied)."""
        bias = self.get_domain_bias(domain, min_n=3)
        if bias and bias.correction_active:
            corrected = max(0.0, min(1.0, forecast - bias.correction_value))
            return corrected, bias.correction_value
        return forecast, 0.0

    # -- Tool 6: calibration_update_archetype_memory --

    def update_archetype_memory(self, run_id: str, memory_base_dir: Path | None = None) -> dict:
        """Write calibration feedback to each archetype's memory:project directory.

        Called after record_outcome(). For each archetype that made predictions
        in this run, generates a natural-language calibration summary and appends
        it to their memory directory.

        Args:
            run_id: The run to summarize
            memory_base_dir: Base directory for agent memory.
                            Default: self.data_dir.parent / "agent-memory"

        Returns:
            { archetypes_updated: int, files_written: [str] }
        """
        if memory_base_dir is None:
            memory_base_dir = self.data_dir.parent / "agent-memory"

        # Find all resolved predictions for this run
        run_preds = [p for p in self._predictions
                     if p["run_id"] == run_id and p["resolved"]]

        if not run_preds:
            return {"archetypes_updated": 0, "files_written": []}

        # Group by archetype
        by_archetype: dict[str, list] = {}
        for pred in run_preds:
            aid = pred["archetype_id"]
            by_archetype.setdefault(aid, []).append(pred)

        files_written = []
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")

        for archetype_id, preds in by_archetype.items():
            arch_dir = memory_base_dir / f"archetype-{archetype_id}"
            arch_dir.mkdir(parents=True, exist_ok=True)

            history_path = arch_dir / "calibration-history.md"
            index_path = arch_dir / "MEMORY.md"

            # Build entry for each prediction in this run
            entries = []
            for pred in preds:
                f = pred["forecast_probability"]
                o = 1.0 if pred["outcome"] else 0.0
                brier = pred.get("brier_score", (f - o) ** 2)
                confidence_pct = round(pred["confidence"] * 100)
                direction = "over" if f > o else "under"
                decision = "Yes" if f >= 0.5 else "No"

                # Domain bias for this archetype
                arch_bias = self.get_archetype_bias(
                    archetype_id, domain=pred["domain"], min_n=1,
                )
                if arch_bias:
                    avg_offset = abs(arch_bias.mean_signed_error)
                    bias_direction = "over" if arch_bias.mean_signed_error > 0 else "under"
                    bias_n = arch_bias.n_observations
                    acq_rate = arch_bias.acquiescence_rate
                else:
                    avg_offset = abs(f - o)
                    bias_direction = direction
                    bias_n = 1
                    acq_rate = f

                entry = (
                    f"## Run {run_id} ({date_str})\n"
                    f"\n"
                    f"**Prediction**: {decision} at {confidence_pct}% "
                    f"| Domain: {pred['domain']} | Horizon: {pred['horizon']}\n"
                    f"**Outcome**: {pred['outcome']} | Brier: {brier:.3f} "
                    f"| Direction: {direction}confident\n"
                    f"**Domain pattern**: Your {pred['domain']} bias: "
                    f"{bias_direction} by {avg_offset:.3f} (n={bias_n})\n"
                    f"**Acquiescence**: Your positive-prediction rate: "
                    f"{acq_rate:.0%} (domain base rate: ~50%)\n"
                    f"\n"
                    f"---\n"
                )
                entries.append(entry)

            # Append to history file
            content = "\n".join(entries) + "\n"
            if history_path.exists():
                existing = history_path.read_text()
                history_path.write_text(existing + content)
            else:
                history_path.write_text(content)
            files_written.append(str(history_path))

            # Create MEMORY.md index if it doesn't exist
            if not index_path.exists():
                archetype_name = archetype_id
                index_content = (
                    f"# Calibration Memory for {archetype_name}\n"
                    f"\n"
                    f"- [calibration-history.md](calibration-history.md)"
                    f" — Prediction outcomes and bias patterns across runs\n"
                )
                index_path.write_text(index_content)
                files_written.append(str(index_path))

        return {
            "archetypes_updated": len(by_archetype),
            "files_written": files_written,
        }

    # -- Tool 7: calibration_update_routing --

    def update_routing(self) -> dict:
        """Update routing recommendations based on A/B comparison data.

        Reads baseline vs deliberation-informed accuracy stratified by
        QuestionComplexity. Writes routing_config.json.

        Returns:
            { routing_config: dict, recommendation: str }
        """
        comparison = self.get_deliberation_comparison()
        strata = comparison["strata"]
        recommendation = comparison["recommendation"]

        # Build routing config from strata
        routing_rules = {}
        for complexity_key, data in strata.items():
            delta = data.get("deliberation_delta")
            helps = data.get("deliberation_helps")

            if helps is True:
                route = "FULL_PIPELINE"
            elif helps is False:
                route = "SKIP_DELIBERATE"
            else:
                route = "FULL_PIPELINE"  # Default when insufficient data

            routing_rules[complexity_key] = {
                "route": route,
                "deliberation_delta": delta,
                "n_baseline": data["n_baseline"],
                "n_informed": data["n_informed"],
                "brier_baseline": data["brier_baseline"],
                "brier_informed": data["brier_informed"],
            }

        routing_config = {
            "routing_rules": routing_rules,
            "recommendation": recommendation,
            "last_updated": datetime.now(UTC).isoformat(),
        }

        routing_path = self.calibration_dir / "routing_config.json"
        with open(routing_path, "w") as f:
            json.dump(routing_config, f, indent=2)

        return {
            "routing_config": routing_config,
            "recommendation": recommendation,
        }

    # -- Tool 8: calibration_rank_archetypes --

    def rank_archetypes(self, min_predictions: int = 5) -> dict:
        """Rank archetypes by prediction accuracy.

        Args:
            min_predictions: Minimum predictions required to be ranked

        Returns:
            { rankings: [{archetype_id, brier, n, rank}],
              top_5: [...], bottom_5: [...],
              needs_regrounding: [...] (corrected-uncorrected gap > 0.05) }
        """
        # Gather per-archetype Brier scores from resolved predictions
        arch_data: dict[str, list[float]] = {}
        for pred in self._predictions:
            if not pred["resolved"] or pred["is_baseline"] or pred["is_bootstrap"]:
                continue
            aid = pred["archetype_id"]
            f = pred["forecast_probability"]
            o = 1.0 if pred["outcome"] else 0.0
            arch_data.setdefault(aid, []).append((f - o) ** 2)

        # Filter by min_predictions and compute averages
        rankings = []
        for aid, scores in arch_data.items():
            if len(scores) < min_predictions:
                continue
            brier = sum(scores) / len(scores)
            rankings.append({
                "archetype_id": aid,
                "brier": round(brier, 6),
                "n": len(scores),
            })

        # Sort by Brier (lower = better)
        rankings.sort(key=lambda x: x["brier"])
        for i, r in enumerate(rankings):
            r["rank"] = i + 1

        top_5 = rankings[:5]
        bottom_5 = rankings[-5:] if len(rankings) >= 5 else rankings[:]

        # Identify archetypes needing regrounding:
        # corrected Brier - uncorrected Brier gap > 0.05
        # i.e., corrections are making this archetype WORSE
        corrections = {}
        for domain in PredictionDomain:
            if domain == PredictionDomain.UNCLASSIFIED:
                continue
            bias = self.get_domain_bias(domain.value, min_n=3)
            if bias and bias.correction_active:
                corrections[domain.value] = bias.correction_value

        needs_regrounding = []
        for entry in rankings:
            aid = entry["archetype_id"]
            arch_preds = [p for p in self._predictions
                          if p["resolved"] and p["archetype_id"] == aid
                          and not p["is_baseline"] and not p["is_bootstrap"]]
            if not arch_preds:
                continue

            brier_raw = self._compute_brier(arch_preds)
            brier_corrected = self._compute_brier_corrected(arch_preds, corrections)

            # If corrected is worse than raw by > 0.05, needs regrounding
            gap = brier_corrected - brier_raw
            if gap > 0.05:
                needs_regrounding.append({
                    "archetype_id": aid,
                    "brier_raw": round(brier_raw, 6),
                    "brier_corrected": round(brier_corrected, 6),
                    "gap": round(gap, 6),
                })

        return {
            "rankings": rankings,
            "top_5": top_5,
            "bottom_5": bottom_5,
            "needs_regrounding": needs_regrounding,
        }

    def _empty_ensemble_metrics(self, n_total: int, n_window: int) -> EnsembleMetrics:
        return EnsembleMetrics(
            brier_raw=0.0, brier_corrected=0.0, brier_gap=0.0,
            brier_baseline=None, brier_informed=None, deliberation_delta=None,
            acquiescence_rate=0.5, n_predictions=n_total, n_resolved=0,
            n_holdout=0, brier_holdout=None, brier_training=None,
            overfitting_gap=None, overfitting_detected=False,
            domain_biases=[], correction_schedule_stage="RECORD_ONLY",
            window_runs=n_window,
        )


def register_tools(app, data_dir: Path) -> None:
    """Register calibration + competence MCP tools on the server."""
    from engine.competence_classifier import classify_question

    engine = CalibrationEngine(data_dir)

    @app.tool()
    async def calibration_record_prediction(
        run_id: str,
        archetype_id: str,
        question_id: str,
        question_text: str,
        forecast_probability: float,
        confidence: float,
        base_rate_anchor: str,
        timeframe: str,
        is_baseline: bool = False,
        is_bootstrap: bool = False,
    ) -> dict:
        """Record a structured prediction for calibration tracking.

        Auto-classifies domain, horizon, complexity. Assigns holdout flag.
        Persists immediately (write-through).

        Args:
            run_id: Current run identifier
            archetype_id: Archetype that made this prediction
            question_id: Unique question identifier
            question_text: The question being predicted
            forecast_probability: Predicted probability [0, 1]
            confidence: Self-assessed confidence [0, 1]
            base_rate_anchor: Historical base rate cited
            timeframe: Expected resolution timeframe (e.g. "3 month", "1 week")
            is_baseline: True if pre-deliberation baseline
            is_bootstrap: True if short-horizon bootstrap question
        """
        pred = engine.record_prediction(
            run_id, archetype_id, question_id, question_text,
            forecast_probability, confidence, base_rate_anchor, timeframe,
            is_baseline, is_bootstrap,
        )
        return pred.model_dump(mode="json")

    @app.tool()
    async def calibration_record_outcome(
        question_id: str,
        run_id: str,
        actual_outcome: bool,
        resolution_source: str,
    ) -> dict:
        """Record the actual outcome for a question and compute Brier scores.

        Triggers Brier score computation for all predictions matching this question.
        Updates domain_corrections.json for debiasing.

        Args:
            question_id: The question that has been resolved
            run_id: Run the question originated from
            actual_outcome: True if event occurred, False if not
            resolution_source: Where the outcome was verified
        """
        return engine.record_outcome(question_id, run_id, actual_outcome, resolution_source)

    @app.tool()
    async def calibration_get_domain_bias(
        domain: str,
        min_n: int = 3,
    ) -> dict:
        """Get directional bias statistics for a prediction domain.

        Positive MSE = ensemble predicts too high (overconfident/acquiescent).
        Uses t-distribution for p-values (not normal CDF).

        Args:
            domain: Domain name (POLICY, ECONOMICS, TECHNOLOGY, SCIENCE, ENVIRONMENT, SOCIAL)
            min_n: Minimum resolved observations required (default 3)
        """
        bias = engine.get_domain_bias(domain, min_n)
        if bias is None:
            return {"error": f"Insufficient data (n < {min_n}) for domain {domain}"}
        return bias.model_dump(mode="json")

    @app.tool()
    async def calibration_get_archetype_bias(
        archetype_id: str,
        domain: str = "",
        min_n: int = 5,
    ) -> dict:
        """Get per-archetype directional bias, optionally filtered by domain.

        Args:
            archetype_id: The archetype to analyze
            domain: Optional domain filter (empty string = all domains)
            min_n: Minimum resolved observations required (default 5)
        """
        d = domain if domain else None
        bias = engine.get_archetype_bias(archetype_id, d, min_n)
        if bias is None:
            return {"error": f"Insufficient data (n < {min_n}) for archetype {archetype_id}"}
        return bias.model_dump(mode="json")

    @app.tool()
    async def calibration_get_ensemble_metrics(
        window: int = 10,
    ) -> dict:
        """Get overall ensemble calibration metrics.

        Compares corrected vs uncorrected Brier, baseline vs informed,
        training vs holdout. Reports correction schedule stage.
        Positive deltas = improvement.

        Args:
            window: Number of most recent runs to include (default 10)
        """
        metrics = engine.get_ensemble_metrics(window)
        return metrics.model_dump(mode="json")

    @app.tool()
    async def calibration_update_archetype_memory(
        run_id: str,
        memory_base_dir: str = "",
    ) -> dict:
        """Write calibration feedback to each archetype's memory directory.

        Called after record_outcome(). For each archetype that made predictions
        in this run, generates a natural-language calibration summary and appends
        it to their memory directory.

        Args:
            run_id: The run to summarize
            memory_base_dir: Base directory for agent memory (empty = default)
        """
        base = Path(memory_base_dir) if memory_base_dir else None
        return engine.update_archetype_memory(run_id, base)

    @app.tool()
    async def calibration_update_routing() -> dict:
        """Update routing recommendations based on A/B comparison data.

        Reads baseline vs deliberation-informed accuracy stratified by
        QuestionComplexity. Writes routing_config.json with per-complexity
        routing rules.
        """
        return engine.update_routing()

    @app.tool()
    async def calibration_rank_archetypes(
        min_predictions: int = 5,
    ) -> dict:
        """Rank archetypes by prediction accuracy (Brier score).

        Returns rankings, top/bottom 5, and archetypes needing regrounding
        (where corrections make predictions worse).

        Args:
            min_predictions: Minimum predictions required to be ranked (default 5)
        """
        return engine.rank_archetypes(min_predictions)

    @app.tool()
    async def competence_classify_question(
        question_text: str,
    ) -> dict:
        """Classify a question for pipeline routing (pre-UNDERSTAND).

        Returns domain, complexity, and routing recommendation:
        - SKIP_DELIBERATE: Simple binary, route to direct amplification
        - FULL_PIPELINE: Multi-factor, needs full deliberation
        - LOW_CONFIDENCE: Unclassifiable, proceed with caveats

        Args:
            question_text: The forecasting question to classify
        """
        assessment = classify_question(question_text, engine)
        return assessment.model_dump(mode="json")


def _t_sf(t_stat: float, df: int) -> float:
    """Survival function (1 - CDF) of the t-distribution.

    SK-03 fix: Replaces normal CDF which was anti-conservative at small n.
    Uses the regularized incomplete beta function relationship:
      P(T > t | df) = 0.5 * I_x(df/2, 1/2)
    where x = df / (df + t^2)
    """
    if df <= 0:
        return 0.5
    x = df / (df + t_stat * t_stat)
    a = df / 2.0
    b = 0.5
    return 0.5 * _betai(a, b, x)


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for incomplete beta function.
    Numerical Recipes algorithm (Lentz's method)."""
    MAXIT = 200
    EPS = 3e-12
    FPMIN = 1e-30

    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d

    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        # Even step
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c

        # Odd step
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta

        if abs(delta - 1.0) < EPS:
            return h

    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log(1.0 - x)
    )

    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    else:
        return 1.0 - bt * _betacf(b, a, 1.0 - x) / b
