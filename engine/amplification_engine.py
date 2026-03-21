"""Amplification engine for OathFish MCP server.

Batch management, result recording, statistical aggregation with file-based debiasing.
3 MCP tools: amplify_init, amplify_record_batch, amplify_aggregate.

Cross-engine contract: reads domain_corrections.json written by Worker B's CalibrationEngine.
Worker A NEVER writes to domain_corrections.json.
"""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    AggregateResult,
    AmplificationConfig,
    AmplificationResult,
    AmplificationState,
    Archetype,
    ArchetypeDistribution,
)
from .persistence import atomic_write_json, read_json


class AmplificationEngine:
    """Batch recording, statistical aggregation, file-based debiasing."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._state: AmplificationState | None = None

    def _state_path(self) -> Path:
        return self._data_dir / "amplification" / "state.json"

    def _persist(self) -> None:
        assert self._state is not None
        atomic_write_json(self._state_path(), self._state)

    def _load(self) -> AmplificationState | None:
        data = read_json(self._state_path())
        if data is None:
            return None
        return AmplificationState.model_validate(data)

    def _ensure_loaded(self) -> AmplificationState:
        if self._state is None:
            self._state = self._load()
        if self._state is None:
            raise ValueError("No active amplification. Call amplify_init first.")
        return self._state

    def _load_domain_corrections(self) -> dict | None:
        """Load domain corrections from calibration file (Worker B writes this).

        Path: ${OATHFISH_DATA_DIR}/calibration/domain_corrections.json
        Returns None if file doesn't exist (expected for runs 1-2).
        """
        corrections_path = self._data_dir.parent / "calibration" / "domain_corrections.json"
        return read_json(corrections_path)

    async def amplify_init(
        self,
        archetypes: list[dict],
        variations_per_archetype: int = 50,
        model: str = "haiku",
        scenario: str = "",
        is_baseline: bool = False,
    ) -> dict:
        """Initialize mass amplification config."""
        parsed_archetypes = [Archetype.model_validate(a) for a in archetypes]
        total_calls = len(parsed_archetypes) * variations_per_archetype
        config_id = f"amp-{uuid.uuid4().hex[:8]}"

        config = AmplificationConfig(
            config_id=config_id,
            archetypes=parsed_archetypes,
            variations_per_archetype=variations_per_archetype,
            model=model,
            scenario=scenario,
            total_calls=total_calls,
            is_baseline=is_baseline,
        )

        self._state = AmplificationState(config=config)
        self._persist()

        return {
            "total_calls": total_calls,
            "estimated_cost": f"~${total_calls * 0.001:.2f}",  # Rough estimate
            "config_id": config_id,
            "is_baseline": is_baseline,
        }

    async def amplify_record_batch(
        self,
        batch_id: str,
        results: list[dict],
    ) -> dict:
        """Record a batch of claude -p results."""
        state = self._ensure_loaded()

        parsed_results = [AmplificationResult.model_validate(r) for r in results]
        state.batches[batch_id] = parsed_results
        state.total_recorded += len(parsed_results)
        self._persist()

        return {
            "batch_id": batch_id,
            "results_recorded": len(parsed_results),
            "running_total": state.total_recorded,
        }

    async def amplify_aggregate(
        self,
        apply_debiasing: bool = False,
        archetype_ids: list[str] | None = None,
    ) -> dict:
        """Compute statistical distributions across all recorded results.

        Debiasing reads from domain_corrections.json (file-based, Worker B writes).
        Returns BOTH raw and debiased distributions (C-28).
        """
        state = self._ensure_loaded()

        # Flatten all results
        all_results: list[AmplificationResult] = []
        for batch in state.batches.values():
            all_results.extend(batch)

        # Filter by archetype_ids if specified
        if archetype_ids:
            all_results = [r for r in all_results if r.archetype_id in archetype_ids]

        if not all_results:
            return AggregateResult(
                per_archetype=[],
                overall={},
                network_effects={},
                raw={},
                debiased={},
                corrections_applied=[],
            ).model_dump(mode="json")

        # Group by archetype
        by_archetype: dict[str, list[AmplificationResult]] = {}
        for r in all_results:
            by_archetype.setdefault(r.archetype_id, []).append(r)

        # Per-archetype distributions
        per_archetype: list[ArchetypeDistribution] = []
        all_actions: list[str] = []
        all_confidences: list[float] = []

        for arch_id, results in by_archetype.items():
            action_counts = Counter(r.action for r in results)
            total = len(results)
            action_dist = {
                action: count / total for action, count in action_counts.items()
            }
            avg_conf = sum(r.confidence for r in results) / total

            # Top themes from reasoning
            theme_counter: Counter = Counter()
            for r in results:
                for word in r.reasoning.lower().split():
                    cleaned = "".join(c for c in word if c.isalnum())
                    if cleaned and len(cleaned) > 4:
                        theme_counter[cleaned] += 1
            top_themes = [w for w, _ in theme_counter.most_common(5)]

            per_archetype.append(ArchetypeDistribution(
                archetype_id=arch_id,
                action_dist=action_dist,
                avg_confidence=avg_conf,
                top_themes=top_themes,
            ))

            all_actions.extend(r.action for r in results)
            all_confidences.extend(r.confidence for r in results)

        # Overall metrics
        total_results = len(all_results)
        action_overall = Counter(all_actions)
        overall = {
            "total_results": total_results,
            "adoption_rate": action_overall.get("adopt", 0) / total_results,
            "rejection_rate": action_overall.get("reject", 0) / total_results,
            "wait_rate": action_overall.get("wait", 0) / total_results,
            "avg_confidence": sum(all_confidences) / total_results,
        }

        # Polarization index: variance of adoption rates across archetypes
        adoption_rates = [
            ad.action_dist.get("adopt", 0.0) for ad in per_archetype
        ]
        if len(adoption_rates) > 1:
            mean_adoption = sum(adoption_rates) / len(adoption_rates)
            variance = sum(
                (r - mean_adoption) ** 2 for r in adoption_rates
            ) / len(adoption_rates)
            overall["polarization_index"] = variance ** 0.5
        else:
            overall["polarization_index"] = 0.0

        # Network effects (simplified)
        network_effects = {
            "viral_potential": overall["adoption_rate"] * overall["avg_confidence"],
            "resistance_clusters": sum(
                1 for ad in per_archetype if ad.action_dist.get("reject", 0) > 0.5
            ),
            "bridge_archetypes": [
                ad.archetype_id
                for ad in per_archetype
                if ad.action_dist.get("adopt", 0) > 0.3
                and ad.action_dist.get("reject", 0) > 0.2
            ],
        }

        # Raw results (always computed)
        raw = {
            "adoption_rate": overall["adoption_rate"],
            "rejection_rate": overall["rejection_rate"],
            "avg_confidence": overall["avg_confidence"],
        }

        # Debiasing
        debiased = dict(raw)  # Start with raw
        corrections_applied: list[dict] = []

        if apply_debiasing:
            corrections_data = self._load_domain_corrections()
            if corrections_data is not None:
                corrections = corrections_data.get("corrections", {})
                stage = corrections_data.get("correction_schedule_stage", "RECORD_ONLY")

                if stage != "RECORD_ONLY":
                    for domain, correction in corrections.items():
                        if not correction.get("correction_active", False):
                            continue
                        offset = correction.get("offset", 0.0)
                        if offset == 0.0:
                            continue

                        # Apply additive correction to confidence
                        adjusted_confidence = max(
                            0.0, min(1.0, raw["avg_confidence"] - offset)
                        )
                        debiased["avg_confidence"] = adjusted_confidence
                        corrections_applied.append({
                            "domain": domain,
                            "offset": offset,
                            "direction": correction.get("direction", "unknown"),
                            "n": correction.get("n", 0),
                        })

        result = AggregateResult(
            per_archetype=per_archetype,
            overall=overall,
            network_effects=network_effects,
            raw=raw,
            debiased=debiased,
            corrections_applied=corrections_applied,
        )

        # Persist aggregate results
        atomic_write_json(
            self._data_dir / "amplification" / "aggregate.json",
            result,
        )

        return result.model_dump(mode="json")


def register_tools(app, data_dir: Path) -> None:
    """Register amplification MCP tools on the server."""
    engine = AmplificationEngine(data_dir)

    @app.tool()
    async def amplify_init(
        archetypes: list[dict],
        variations_per_archetype: int = 50,
        model: str = "haiku",
        scenario: str = "",
        is_baseline: bool = False,
    ) -> dict:
        """Initialize mass amplification config for claude -p batch calls.

        Args:
            archetypes: Archetype dicts (with or without evolved positions)
            variations_per_archetype: Persona variations per archetype (default 50)
            model: Model for claude -p calls (default haiku)
            scenario: The prompt scenario each variation receives
            is_baseline: True for BASELINE_AMPLIFY phase (pre-deliberation control)
        """
        return await engine.amplify_init(
            archetypes, variations_per_archetype, model, scenario, is_baseline
        )

    @app.tool()
    async def amplify_record_batch(
        batch_id: str,
        results: list[dict],
    ) -> dict:
        """Record a batch of claude -p amplification results.

        Args:
            batch_id: Unique batch identifier
            results: List of AmplificationResult dicts (persona_id, archetype_id, action, reasoning, confidence)
        """
        return await engine.amplify_record_batch(batch_id, results)

    @app.tool()
    async def amplify_aggregate(
        apply_debiasing: bool = False,
        archetype_ids: list[str] | None = None,
    ) -> dict:
        """Compute statistical distributions across all recorded amplification results.

        Returns per-archetype distributions, overall metrics, network effects,
        and both raw + debiased results (C-28).

        Args:
            apply_debiasing: Apply calibration corrections from domain_corrections.json (default False)
            archetype_ids: Filter to specific archetype IDs (None = all, for pagination)
        """
        return await engine.amplify_aggregate(apply_debiasing, archetype_ids)
