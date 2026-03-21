"""B-H04: Holdout set contamination.

Mitigation: Hash-based deterministic partition; exclude_holdout=True default.
Attack: Verify holdout predictions cannot influence correction values.
"""

import tempfile
from pathlib import Path
from engine.calibration_engine import CalibrationEngine
from engine.domain_classifier import compute_holdout_flag, generate_prediction_id


class TestBH04HoldoutContamination:
    """Attack: Try to contaminate corrections with holdout data."""

    def test_holdout_excluded_from_bias_by_default(self):
        """get_domain_bias exclude_holdout defaults to True."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            # Create ONLY holdout predictions
            holdout_count = 0
            i = 0
            while holdout_count < 20:
                pid = generate_prediction_id("r1", "a1", f"q-{i}")
                if compute_holdout_flag(pid):
                    engine.record_prediction(
                        run_id="r1", archetype_id="a1",
                        question_id=f"q-{i}",
                        question_text="Will the regulation law government policy pass?",
                        forecast_probability=0.9,
                        confidence=0.9,
                        base_rate_anchor="test", timeframe="3 month",
                    )
                    engine.record_outcome(f"q-{i}", "r1", False, "test")
                    holdout_count += 1
                i += 1

            # With exclude_holdout=True (default), should have insufficient data
            bias = engine.get_domain_bias("POLICY", min_n=3, exclude_holdout=True)
            assert bias is None, "Holdout-only data should not produce bias results"

    def test_corrections_file_not_influenced_by_holdout(self):
        """write_domain_corrections should use exclude_holdout=True."""
        import json
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            # Mix of holdout and training predictions
            for run_idx in range(5):
                for i in range(20):
                    engine.record_prediction(
                        run_id=f"r{run_idx}", archetype_id="a1",
                        question_id=f"q-{run_idx}-{i}",
                        question_text="Will the regulation law government policy pass?",
                        forecast_probability=0.8,
                        confidence=0.9,
                        base_rate_anchor="test", timeframe="3 month",
                    )
                    engine.record_outcome(
                        f"q-{run_idx}-{i}", f"r{run_idx}", False, "test"
                    )

            engine.write_domain_corrections()

            with open(engine.corrections_file) as f:
                data = json.load(f)

            # Verify corrections were written
            if "POLICY" in data["corrections"]:
                n_correction = data["corrections"]["POLICY"]["n"]
                # n should be less than total (some held out)
                total_policy = sum(1 for p in engine._predictions
                                   if p["resolved"] and p["domain"] == "POLICY"
                                   and not p["is_baseline"])
                holdout_policy = sum(1 for p in engine._predictions
                                     if p["resolved"] and p["domain"] == "POLICY"
                                     and p["is_holdout"] and not p["is_baseline"])
                # n in corrections should exclude holdout
                assert n_correction <= total_policy - holdout_policy + 1, \
                    f"Corrections n ({n_correction}) should exclude holdout ({holdout_policy})"
