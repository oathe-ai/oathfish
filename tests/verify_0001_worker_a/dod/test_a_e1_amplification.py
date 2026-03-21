"""DoD A-E.1: engine/amplification_engine.py -- Aggregation works; debiasing applies/skips gracefully.

Spec claims:
- amplify_init, amplify_record_batch, amplify_aggregate
- amplify_aggregate(apply_debiasing=False, archetype_ids=None)
- Debiasing reads domain_corrections.json (file-based)
- Returns BOTH raw and debiased distributions (C-28)
- Graceful degradation when calibration file absent
- Baseline results stored separately (is_baseline flag)
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

import pytest
from engine.amplification_engine import AmplificationEngine


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


SAMPLE_ARCHETYPES = [
    {"id": "arch-0", "name": "Historian", "segment": "structural"},
    {"id": "arch-1", "name": "Contrarian", "segment": "structural"},
]

SAMPLE_RESULTS = [
    {"persona_id": "p-0", "archetype_id": "arch-0", "action": "adopt", "reasoning": "Growth potential", "confidence": 0.8},
    {"persona_id": "p-1", "archetype_id": "arch-0", "action": "wait", "reasoning": "Uncertain timing", "confidence": 0.5},
    {"persona_id": "p-2", "archetype_id": "arch-1", "action": "reject", "reasoning": "Risk averse concern", "confidence": 0.9},
    {"persona_id": "p-3", "archetype_id": "arch-1", "action": "adopt", "reasoning": "Innovation driver growth", "confidence": 0.7},
]


class TestAmplifyInit:
    def test_creates_config(self, tmp_path):
        engine = AmplificationEngine(tmp_path)
        result = run_async(engine.amplify_init(SAMPLE_ARCHETYPES, scenario="AI regulation impact"))
        assert "config_id" in result
        assert result["total_calls"] == 100  # 2 archetypes * 50 variations

    def test_is_baseline_flag(self, tmp_path):
        engine = AmplificationEngine(tmp_path)
        result = run_async(engine.amplify_init(SAMPLE_ARCHETYPES, is_baseline=True))
        assert result["is_baseline"] is True


class TestAmplifyRecordBatch:
    def test_records_batch(self, tmp_path):
        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init(SAMPLE_ARCHETYPES))
        result = run_async(engine.amplify_record_batch("batch-1", SAMPLE_RESULTS))
        assert result["results_recorded"] == 4
        assert result["running_total"] == 4

    def test_multiple_batches_accumulate(self, tmp_path):
        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init(SAMPLE_ARCHETYPES))
        run_async(engine.amplify_record_batch("batch-1", SAMPLE_RESULTS[:2]))
        result = run_async(engine.amplify_record_batch("batch-2", SAMPLE_RESULTS[2:]))
        assert result["running_total"] == 4


class TestAmplifyAggregate:
    def test_aggregate_returns_distributions(self, tmp_path):
        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init(SAMPLE_ARCHETYPES))
        run_async(engine.amplify_record_batch("batch-1", SAMPLE_RESULTS))
        result = run_async(engine.amplify_aggregate())
        assert "per_archetype" in result
        assert "overall" in result
        assert "raw" in result
        assert "debiased" in result

    def test_aggregate_returns_both_raw_and_debiased(self, tmp_path):
        """C-28: Returns BOTH corrected and uncorrected."""
        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init(SAMPLE_ARCHETYPES))
        run_async(engine.amplify_record_batch("batch-1", SAMPLE_RESULTS))
        result = run_async(engine.amplify_aggregate())
        assert "raw" in result
        assert "debiased" in result
        assert "adoption_rate" in result["raw"]
        assert "rejection_rate" in result["raw"]

    def test_aggregate_per_archetype_distributions(self, tmp_path):
        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init(SAMPLE_ARCHETYPES))
        run_async(engine.amplify_record_batch("batch-1", SAMPLE_RESULTS))
        result = run_async(engine.amplify_aggregate())
        per_arch = result["per_archetype"]
        assert len(per_arch) == 2
        for arch_dist in per_arch:
            assert "action_dist" in arch_dist
            assert "avg_confidence" in arch_dist

    def test_aggregate_filter_by_archetype_ids(self, tmp_path):
        """A-H07: Pagination parameter."""
        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init(SAMPLE_ARCHETYPES))
        run_async(engine.amplify_record_batch("batch-1", SAMPLE_RESULTS))
        result = run_async(engine.amplify_aggregate(archetype_ids=["arch-0"]))
        per_arch = result["per_archetype"]
        assert len(per_arch) == 1
        assert per_arch[0]["archetype_id"] == "arch-0"

    def test_aggregate_empty_results(self, tmp_path):
        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init(SAMPLE_ARCHETYPES))
        result = run_async(engine.amplify_aggregate())
        assert result["per_archetype"] == []


class TestDebiasing:
    """Spec A-H03: File-based debiasing, graceful degradation."""

    def test_no_corrections_file_graceful(self, tmp_path):
        """Spec: Graceful degradation when calibration file absent."""
        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init(SAMPLE_ARCHETYPES))
        run_async(engine.amplify_record_batch("batch-1", SAMPLE_RESULTS))
        # apply_debiasing=True but no file: should not crash
        result = run_async(engine.amplify_aggregate(apply_debiasing=True))
        assert "debiased" in result
        assert "corrections_applied" in result

    def test_debiasing_applies_corrections(self, tmp_path):
        """Spec: Correction formula: adjusted = clamp(raw - offset, 0, 1)."""
        # Create the corrections file where the engine expects it
        # The engine looks at self._data_dir.parent / "calibration" / "domain_corrections.json"
        cal_dir = tmp_path.parent / "calibration"
        cal_dir.mkdir(parents=True, exist_ok=True)
        corrections = {
            "corrections": {
                "TECHNOLOGY": {"offset": 0.05, "n": 95, "direction": "over", "p_value": 0.03, "correction_active": True},
            },
            "last_updated": "2026-03-18T10:00:00Z",
            "correction_schedule_stage": "DOMAIN_ADDITIVE",
        }
        with open(cal_dir / "domain_corrections.json", "w") as f:
            json.dump(corrections, f)

        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init(SAMPLE_ARCHETYPES))
        run_async(engine.amplify_record_batch("batch-1", SAMPLE_RESULTS))
        result = run_async(engine.amplify_aggregate(apply_debiasing=True))
        assert len(result["corrections_applied"]) > 0

    def test_debiasing_skips_inactive_corrections(self, tmp_path):
        cal_dir = tmp_path.parent / "calibration"
        cal_dir.mkdir(parents=True, exist_ok=True)
        corrections = {
            "corrections": {
                "TECHNOLOGY": {"offset": 0.05, "n": 40, "direction": "over", "p_value": 0.45, "correction_active": False},
            },
            "last_updated": "2026-03-18T10:00:00Z",
            "correction_schedule_stage": "DOMAIN_ADDITIVE",
        }
        with open(cal_dir / "domain_corrections.json", "w") as f:
            json.dump(corrections, f)

        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init(SAMPLE_ARCHETYPES))
        run_async(engine.amplify_record_batch("batch-1", SAMPLE_RESULTS))
        result = run_async(engine.amplify_aggregate(apply_debiasing=True))
        assert len(result["corrections_applied"]) == 0

    def test_debiasing_skips_record_only_stage(self, tmp_path):
        """Spec: RECORD_ONLY stage means no corrections applied."""
        cal_dir = tmp_path.parent / "calibration"
        cal_dir.mkdir(parents=True, exist_ok=True)
        corrections = {
            "corrections": {
                "TECHNOLOGY": {"offset": 0.05, "n": 95, "direction": "over", "p_value": 0.03, "correction_active": True},
            },
            "last_updated": "2026-03-18T10:00:00Z",
            "correction_schedule_stage": "RECORD_ONLY",
        }
        with open(cal_dir / "domain_corrections.json", "w") as f:
            json.dump(corrections, f)

        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init(SAMPLE_ARCHETYPES))
        run_async(engine.amplify_record_batch("batch-1", SAMPLE_RESULTS))
        result = run_async(engine.amplify_aggregate(apply_debiasing=True))
        assert len(result["corrections_applied"]) == 0
