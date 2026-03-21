"""B-H07: Domain-varying acquiescence.

Mitigation: Per-domain corrections, not global.
Attack: Create data with different bias per domain and verify per-domain correction.
"""

import tempfile
from pathlib import Path
from engine.calibration_engine import CalibrationEngine


class TestBH07DomainVaryingAcquiescence:
    """Attack: Verify corrections are per-domain, not global."""

    def test_different_domains_different_corrections(self):
        """Two domains with opposite biases should get different correction values."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))

            for run_idx in range(5):
                # TECHNOLOGY: overconfident (too high)
                for i in range(10):
                    engine.record_prediction(
                        run_id=f"r{run_idx}", archetype_id="a1",
                        question_id=f"q-tech-{run_idx}-{i}",
                        question_text="Will the technology software platform AI product launch?",
                        forecast_probability=0.85,
                        confidence=0.7,
                        base_rate_anchor="test", timeframe="3 month",
                    )
                    engine.record_outcome(
                        f"q-tech-{run_idx}-{i}", f"r{run_idx}", False, "test"
                    )

                # POLICY: underconfident (too low)
                for i in range(10):
                    engine.record_prediction(
                        run_id=f"r{run_idx}", archetype_id="a1",
                        question_id=f"q-policy-{run_idx}-{i}",
                        question_text="Will the regulation law government policy election pass?",
                        forecast_probability=0.15,
                        confidence=0.7,
                        base_rate_anchor="test", timeframe="3 month",
                    )
                    engine.record_outcome(
                        f"q-policy-{run_idx}-{i}", f"r{run_idx}", True, "test"
                    )

            tech_bias = engine.get_domain_bias("TECHNOLOGY", min_n=3)
            policy_bias = engine.get_domain_bias("POLICY", min_n=3)

            assert tech_bias is not None
            assert policy_bias is not None

            # Technology should be overconfident (positive MSE)
            assert tech_bias.mean_signed_error > 0, \
                f"TECHNOLOGY should be overconfident, got MSE={tech_bias.mean_signed_error}"
            # Policy should be underconfident (negative MSE)
            assert policy_bias.mean_signed_error < 0, \
                f"POLICY should be underconfident, got MSE={policy_bias.mean_signed_error}"

            # Corrections should be in opposite directions
            if tech_bias.correction_active and policy_bias.correction_active:
                assert tech_bias.correction_value > 0
                assert policy_bias.correction_value < 0, \
                    "Underconfident domain should have negative correction"

    def test_uncorrected_domain_not_affected(self):
        """A domain with no data should not receive any correction."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            # Only add TECHNOLOGY data
            for i in range(10):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="Will the technology software platform launch?",
                    forecast_probability=0.7, confidence=0.7,
                    base_rate_anchor="test", timeframe="3 month",
                )
                engine.record_outcome(f"q-{i}", "r1", (i % 2 == 0), "test")

            # SCIENCE should have no data, no correction
            corrected, offset = engine.apply_correction(0.7, "SCIENCE")
            assert offset == 0.0, \
                f"Domain with no data should have 0 correction, got {offset}"
            assert corrected == 0.7
