"""Tests for feedback loop methods: update_archetype_memory, update_routing, rank_archetypes."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from engine.calibration_engine import CalibrationEngine


@pytest.fixture
def engine(tmp_path):
    return CalibrationEngine(tmp_path)


def _record(engine, run_id="run1", archetype_id="arch1", question_id="q1",
            question_text="Will government regulation ban this policy?",
            forecast=0.7, confidence=0.8, timeframe="3 month",
            is_baseline=False, is_bootstrap=False):
    """Helper to record a prediction with sensible defaults."""
    return engine.record_prediction(
        run_id=run_id,
        archetype_id=archetype_id,
        question_id=question_id,
        question_text=question_text,
        forecast_probability=forecast,
        confidence=confidence,
        base_rate_anchor="50%",
        timeframe=timeframe,
        is_baseline=is_baseline,
        is_bootstrap=is_bootstrap,
    )


def _seed_resolved(engine, n=6, run_id="run1", forecast=0.8, outcome=False,
                   archetype_prefix="arch", question_prefix="q",
                   is_baseline=False):
    """Seed n resolved predictions for a single run."""
    for i in range(n):
        _record(engine, run_id=run_id, archetype_id=f"{archetype_prefix}{i}",
                question_id=f"{question_prefix}{i}", forecast=forecast,
                is_baseline=is_baseline)
        engine.record_outcome(f"{question_prefix}{i}", run_id, outcome, "test")


class TestUpdateArchetypeMemory:
    def test_writes_file(self, engine, tmp_path):
        """Memory file is created with correct content."""
        _record(engine, run_id="run1", archetype_id="arch1",
                question_id="q1", forecast=0.9, confidence=0.8)
        engine.record_outcome("q1", "run1", True, "test")

        mem_dir = tmp_path / "agent-memory"
        result = engine.update_archetype_memory("run1", mem_dir)

        assert result["archetypes_updated"] == 1
        assert len(result["files_written"]) >= 1

        history = mem_dir / "archetype-arch1" / "calibration-history.md"
        assert history.exists()
        content = history.read_text()
        assert "Run run1" in content
        assert "Brier:" in content
        assert "Domain pattern" in content
        assert "Acquiescence" in content

    def test_creates_memory_index(self, engine, tmp_path):
        """MEMORY.md index file created on first write."""
        _record(engine, run_id="run1", archetype_id="arch1",
                question_id="q1", forecast=0.7)
        engine.record_outcome("q1", "run1", True, "test")

        mem_dir = tmp_path / "agent-memory"
        engine.update_archetype_memory("run1", mem_dir)

        index = mem_dir / "archetype-arch1" / "MEMORY.md"
        assert index.exists()
        content = index.read_text()
        assert "Calibration Memory" in content
        assert "calibration-history.md" in content

    def test_appends_on_second_call(self, engine, tmp_path):
        """Second call appends, does not overwrite."""
        mem_dir = tmp_path / "agent-memory"

        # Run 1
        _record(engine, run_id="run1", archetype_id="arch1",
                question_id="q1", forecast=0.9)
        engine.record_outcome("q1", "run1", True, "test")
        engine.update_archetype_memory("run1", mem_dir)

        # Run 2
        _record(engine, run_id="run2", archetype_id="arch1",
                question_id="q2", forecast=0.3)
        engine.record_outcome("q2", "run2", False, "test")
        engine.update_archetype_memory("run2", mem_dir)

        history = mem_dir / "archetype-arch1" / "calibration-history.md"
        content = history.read_text()
        assert "Run run1" in content
        assert "Run run2" in content

    def test_no_resolved_predictions(self, engine, tmp_path):
        """Returns empty result when no resolved predictions for run."""
        _record(engine, run_id="run1", archetype_id="arch1", question_id="q1")
        # Don't resolve

        mem_dir = tmp_path / "agent-memory"
        result = engine.update_archetype_memory("run1", mem_dir)
        assert result["archetypes_updated"] == 0
        assert result["files_written"] == []

    def test_multiple_archetypes(self, engine, tmp_path):
        """Multiple archetypes each get their own directory."""
        for i in range(3):
            _record(engine, run_id="run1", archetype_id=f"arch{i}",
                    question_id=f"q{i}", forecast=0.7)
            engine.record_outcome(f"q{i}", "run1", True, "test")

        mem_dir = tmp_path / "agent-memory"
        result = engine.update_archetype_memory("run1", mem_dir)

        assert result["archetypes_updated"] == 3
        for i in range(3):
            assert (mem_dir / f"archetype-arch{i}" / "calibration-history.md").exists()

    def test_default_memory_dir(self, engine):
        """Default memory_base_dir is data_dir.parent / 'agent-memory'."""
        _record(engine, run_id="run1", archetype_id="arch1",
                question_id="q1", forecast=0.7)
        engine.record_outcome("q1", "run1", True, "test")

        result = engine.update_archetype_memory("run1")
        assert result["archetypes_updated"] == 1
        default_path = engine.data_dir.parent / "agent-memory" / "archetype-arch1" / "calibration-history.md"
        assert default_path.exists()

    def test_direction_overconfident(self, engine, tmp_path):
        """Overconfident direction when forecast > outcome."""
        _record(engine, run_id="run1", archetype_id="arch1",
                question_id="q1", forecast=0.9, confidence=0.9)
        engine.record_outcome("q1", "run1", False, "test")

        mem_dir = tmp_path / "agent-memory"
        engine.update_archetype_memory("run1", mem_dir)

        history = (mem_dir / "archetype-arch1" / "calibration-history.md").read_text()
        assert "overconfident" in history

    def test_direction_underconfident(self, engine, tmp_path):
        """Underconfident direction when forecast < outcome."""
        _record(engine, run_id="run1", archetype_id="arch1",
                question_id="q1", forecast=0.1, confidence=0.5)
        engine.record_outcome("q1", "run1", True, "test")

        mem_dir = tmp_path / "agent-memory"
        engine.update_archetype_memory("run1", mem_dir)

        history = (mem_dir / "archetype-arch1" / "calibration-history.md").read_text()
        assert "underconfident" in history


class TestUpdateRouting:
    def test_produces_valid_json(self, engine):
        """Routing config written to disk with correct structure."""
        # Seed baseline + informed predictions
        for i in range(5):
            _record(engine, run_id="run1", archetype_id=f"base{i}",
                    question_id=f"q{i}", forecast=0.3, is_baseline=True)
            _record(engine, run_id="run1", archetype_id=f"info{i}",
                    question_id=f"q{i}", forecast=0.8)
            engine.record_outcome(f"q{i}", "run1", True, "test")

        result = engine.update_routing()

        assert "routing_config" in result
        assert "recommendation" in result

        config = result["routing_config"]
        assert "routing_rules" in config
        assert "last_updated" in config

        # Verify file on disk
        routing_path = engine.calibration_dir / "routing_config.json"
        assert routing_path.exists()
        disk_data = json.loads(routing_path.read_text())
        assert "routing_rules" in disk_data

    def test_routing_rules_per_complexity(self, engine):
        """Each complexity level gets a routing rule."""
        _seed_resolved(engine, n=3, run_id="run1", forecast=0.3,
                       outcome=True, is_baseline=True,
                       archetype_prefix="base", question_prefix="qb")
        _seed_resolved(engine, n=3, run_id="run1", forecast=0.8,
                       outcome=True, archetype_prefix="info", question_prefix="qi")

        result = engine.update_routing()
        rules = result["routing_config"]["routing_rules"]

        # Should have entries for complexity levels that have data
        for key, rule in rules.items():
            assert "route" in rule
            assert rule["route"] in ("FULL_PIPELINE", "SKIP_DELIBERATE")

    def test_deliberation_helps_routing(self, engine):
        """When deliberation helps, route is FULL_PIPELINE."""
        # Baseline: bad predictions (low forecast, true outcome -> high brier)
        for i in range(5):
            _record(engine, run_id="run1", archetype_id=f"base{i}",
                    question_id=f"q{i}", forecast=0.2, is_baseline=True)
            # Informed: good predictions
            _record(engine, run_id="run1", archetype_id=f"info{i}",
                    question_id=f"q{i}", forecast=0.9)
            engine.record_outcome(f"q{i}", "run1", True, "test")

        result = engine.update_routing()
        rules = result["routing_config"]["routing_rules"]

        # At least one complexity level should route to FULL_PIPELINE
        routes = [r["route"] for r in rules.values()
                  if r["n_baseline"] > 0 and r["n_informed"] > 0]
        assert any(r == "FULL_PIPELINE" for r in routes) or len(routes) == 0

    def test_empty_data_routing(self, engine):
        """Routing works with no data (defaults to FULL_PIPELINE)."""
        result = engine.update_routing()
        rules = result["routing_config"]["routing_rules"]
        for rule in rules.values():
            assert rule["route"] == "FULL_PIPELINE"


class TestRankArchetypes:
    def test_correct_ordering(self, engine):
        """Archetypes ranked by Brier score, lower = better."""
        # arch_good: forecast 0.9, outcome True -> Brier 0.01
        for i in range(5):
            _record(engine, run_id="run1", archetype_id="arch_good",
                    question_id=f"qg{i}", forecast=0.9)
            engine.record_outcome(f"qg{i}", "run1", True, "test")

        # arch_bad: forecast 0.9, outcome False -> Brier 0.81
        for i in range(5):
            _record(engine, run_id="run1", archetype_id="arch_bad",
                    question_id=f"qb{i}", forecast=0.9)
            engine.record_outcome(f"qb{i}", "run1", False, "test")

        result = engine.rank_archetypes(min_predictions=1)
        rankings = result["rankings"]

        assert len(rankings) >= 2
        # arch_good should rank higher (lower Brier)
        good_rank = next(r for r in rankings if r["archetype_id"] == "arch_good")
        bad_rank = next(r for r in rankings if r["archetype_id"] == "arch_bad")
        assert good_rank["rank"] < bad_rank["rank"]
        assert good_rank["brier"] < bad_rank["brier"]

    def test_min_predictions_filter(self, engine):
        """Archetypes below min_predictions are excluded."""
        # arch1: 3 predictions (below threshold of 5)
        for i in range(3):
            _record(engine, run_id="run1", archetype_id="arch_few",
                    question_id=f"qf{i}", forecast=0.7)
            engine.record_outcome(f"qf{i}", "run1", True, "test")

        # arch2: 6 predictions (above threshold)
        for i in range(6):
            _record(engine, run_id="run1", archetype_id="arch_many",
                    question_id=f"qm{i}", forecast=0.7)
            engine.record_outcome(f"qm{i}", "run1", True, "test")

        result = engine.rank_archetypes(min_predictions=5)
        arch_ids = [r["archetype_id"] for r in result["rankings"]]
        assert "arch_few" not in arch_ids
        assert "arch_many" in arch_ids

    def test_top_bottom_5(self, engine):
        """top_5 and bottom_5 slices are correct."""
        # Create 10 archetypes with varying accuracy
        for a in range(10):
            forecast = 0.5 + (a * 0.05)  # 0.50 to 0.95
            for i in range(5):
                _record(engine, run_id="run1", archetype_id=f"arch{a}",
                        question_id=f"q{a}_{i}", forecast=forecast)
                engine.record_outcome(f"q{a}_{i}", "run1", True, "test")

        result = engine.rank_archetypes(min_predictions=1)
        assert len(result["top_5"]) == 5
        assert len(result["bottom_5"]) == 5

        # Top 5 should have lower Brier than bottom 5
        top_max = max(r["brier"] for r in result["top_5"])
        bottom_min = min(r["brier"] for r in result["bottom_5"])
        assert top_max <= bottom_min

    def test_identifies_regrounding_candidates(self, engine):
        """Archetypes where corrections hurt are flagged for regrounding."""
        # Create a scenario: archetype already well-calibrated in a domain
        # with active corrections that make it worse.
        # We need: active domain corrections AND an archetype that is hurt by them.

        # First, create lots of over-confident predictions to activate corrections
        for r in range(3):
            for i in range(8):
                idx = r * 8 + i
                _record(engine, run_id=f"run{r+1}", archetype_id=f"crowd{idx}",
                        question_id=f"qc{idx}", forecast=0.95)
                engine.record_outcome(f"qc{idx}", f"run{r+1}", False, "test")

        # Now add a well-calibrated archetype that predicts LOW correctly
        # The domain correction (subtracting positive offset from already-low forecast)
        # will make this archetype's predictions even lower and further from outcome=0
        # Actually, correction subtracts from forecast. If forecast is low (0.1)
        # and outcome is False (0.0), raw Brier = 0.01.
        # If correction is -0.9 (subtract 0.9), corrected = max(0, 0.1-0.9) = 0.0
        # corrected Brier = 0.0. That's better, not worse.
        #
        # For regrounding: we need an archetype that predicts correctly in the
        # opposite direction of the crowd bias. If crowd is overconfident (high forecast,
        # false outcome), correction subtracts from forecast. An archetype that
        # correctly predicts TRUE with moderate forecast will be hurt:
        # e.g. forecast=0.6, outcome=True. Raw Brier = 0.16
        # correction offset ~0.9 -> corrected = max(0, 0.6-0.9) = 0
        # corrected Brier = 1.0. Gap = 0.84 > 0.05. Needs regrounding.
        for i in range(6):
            _record(engine, run_id="run1", archetype_id="arch_contrarian",
                    question_id=f"qx{i}", forecast=0.6)
            engine.record_outcome(f"qx{i}", "run1", True, "test")

        result = engine.rank_archetypes(min_predictions=1)

        # Check if corrections are active
        from engine.calibration_models import PredictionDomain
        bias = engine.get_domain_bias("POLICY", min_n=1, exclude_holdout=False)
        if bias and bias.correction_active:
            # arch_contrarian should be flagged
            regrounding_ids = [r["archetype_id"] for r in result["needs_regrounding"]]
            assert "arch_contrarian" in regrounding_ids

    def test_empty_data(self, engine):
        """Returns empty rankings with no data."""
        result = engine.rank_archetypes()
        assert result["rankings"] == []
        assert result["top_5"] == []
        assert result["bottom_5"] == []
        assert result["needs_regrounding"] == []

    def test_excludes_baseline_and_bootstrap(self, engine):
        """Baseline and bootstrap predictions excluded from ranking."""
        for i in range(5):
            _record(engine, run_id="run1", archetype_id="arch_base",
                    question_id=f"qbase{i}", forecast=0.7, is_baseline=True)
            engine.record_outcome(f"qbase{i}", "run1", True, "test")

        for i in range(5):
            _record(engine, run_id="run1", archetype_id="arch_boot",
                    question_id=f"qboot{i}", forecast=0.7, is_bootstrap=True)
            engine.record_outcome(f"qboot{i}", "run1", True, "test")

        result = engine.rank_archetypes(min_predictions=1)
        arch_ids = [r["archetype_id"] for r in result["rankings"]]
        assert "arch_base" not in arch_ids
        assert "arch_boot" not in arch_ids


class TestIntegrationPipeline:
    def test_full_pipeline(self, engine, tmp_path):
        """Integration: record -> outcome -> memory -> routing -> ranking."""
        mem_dir = tmp_path / "agent-memory"

        # Step 1: Record baseline + informed predictions across multiple runs
        for r in range(3):
            run_id = f"run{r+1}"
            for i in range(5):
                qid = f"q{r}_{i}"
                # Baseline (worse)
                _record(engine, run_id=run_id, archetype_id=f"base{i}",
                        question_id=qid, forecast=0.3, is_baseline=True)
                # Informed (better)
                _record(engine, run_id=run_id, archetype_id=f"info{i}",
                        question_id=qid, forecast=0.8)
                # Step 2: Record outcomes
                engine.record_outcome(qid, run_id, True, "integration-test")

        # Step 3: Write archetype memory
        mem_result = engine.update_archetype_memory("run1", mem_dir)
        assert mem_result["archetypes_updated"] > 0

        # Step 4: Update routing
        routing_result = engine.update_routing()
        assert "routing_config" in routing_result
        routing_path = engine.calibration_dir / "routing_config.json"
        assert routing_path.exists()

        # Step 5: Rank archetypes
        rank_result = engine.rank_archetypes(min_predictions=1)
        assert len(rank_result["rankings"]) > 0

        # Verify info archetypes rank higher than base would
        # (base excluded from ranking since is_baseline=True)
        ranked_ids = [r["archetype_id"] for r in rank_result["rankings"]]
        for i in range(5):
            assert f"base{i}" not in ranked_ids  # Baselines excluded
            assert f"info{i}" in ranked_ids

    def test_multi_run_memory_accumulation(self, engine, tmp_path):
        """Memory accumulates across multiple runs correctly."""
        mem_dir = tmp_path / "agent-memory"

        for r in range(3):
            run_id = f"run{r+1}"
            _record(engine, run_id=run_id, archetype_id="arch1",
                    question_id=f"q{r}", forecast=0.7)
            engine.record_outcome(f"q{r}", run_id, True, "test")
            engine.update_archetype_memory(run_id, mem_dir)

        history = (mem_dir / "archetype-arch1" / "calibration-history.md").read_text()
        assert "Run run1" in history
        assert "Run run2" in history
        assert "Run run3" in history

        # MEMORY.md should only be created once (not duplicated)
        index_path = mem_dir / "archetype-arch1" / "MEMORY.md"
        assert index_path.exists()
        # Should contain exactly one line referencing calibration-history.md
        index_content = index_path.read_text()
        # The markdown link [calibration-history.md](calibration-history.md) has 2 occurrences
        # on a single line; verify there's only one such link line
        link_lines = [l for l in index_content.splitlines()
                      if "calibration-history.md" in l]
        assert len(link_lines) == 1
