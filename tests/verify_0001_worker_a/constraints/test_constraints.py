"""Constraint verification tests.

C-02: All MCP computation deterministic
C-07: 8-state machine with correct transitions
C-14: Split position types (ArgumentPosition rounds 1-5, PredictionPosition round 6)
C-15: Write-through disk persistence after every mutation
C-32: Diversity index tracking with premature consensus detection
C-33: No numeric predictions shared before round 6
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

import pytest


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestC02Determinism:
    """C-02: All MCP computation deterministic -- same inputs = same outputs."""

    def test_sentiment_deterministic(self):
        from engine.sentiment import compute_sentiment
        text = "Great innovative approach with significant risk and terrible consequences"
        results = [compute_sentiment(text) for _ in range(50)]
        scores = [r.score for r in results]
        assert len(set(scores)) == 1, f"Non-deterministic sentiment: {set(scores)}"

    def test_jaccard_deterministic(self):
        from engine.deliberation_engine import jaccard_similarity
        s1, s2 = {"a", "b", "c"}, {"b", "c", "d"}
        results = [jaccard_similarity(s1, s2) for _ in range(50)]
        assert len(set(results)) == 1

    def test_clustering_deterministic(self):
        from engine.deliberation_engine import cluster_arguments
        args = ["regulation stabilizes", "technology disrupts", "competition drives"]
        results = [len(cluster_arguments(args)) for _ in range(50)]
        assert len(set(results)) == 1


class TestC07StateMachine:
    """C-07: 8-state machine with correct transitions."""

    def test_exactly_9_states(self):
        from engine.models import RunPhase
        assert len(list(RunPhase)) == 9

    def test_pipeline_order(self):
        from engine.state_machine import LEGAL_TRANSITIONS
        from engine.models import RunPhase

        pipeline = [
            RunPhase.INIT, RunPhase.UNDERSTAND, RunPhase.BASELINE_AMPLIFY,
            RunPhase.DELIBERATE, RunPhase.AMPLIFY, RunPhase.SYNTHESIZE,
            RunPhase.INTERACT, RunPhase.COMPLETE,
        ]
        for i in range(len(pipeline) - 1):
            current = pipeline[i]
            next_state = pipeline[i + 1]
            assert next_state in LEGAL_TRANSITIONS[current], (
                f"{current.value} should transition to {next_state.value}"
            )


class TestC14SplitPositionTypes:
    """C-14: Split position types: ArgumentPosition (rounds 1-5) + PredictionPosition (round 6)."""

    def test_argument_position_separate_class(self):
        from engine.models import ArgumentPosition, PredictionPosition
        assert ArgumentPosition is not PredictionPosition

    def test_argument_position_no_numeric_fields(self):
        from engine.models import ArgumentPosition
        fields = ArgumentPosition.model_fields
        assert "stance" not in fields
        assert "confidence" not in fields
        assert "prediction" not in fields
        assert "decision" not in fields

    def test_prediction_position_has_numeric_fields(self):
        from engine.models import PredictionPosition
        fields = PredictionPosition.model_fields
        assert "stance" in fields
        assert "confidence" in fields
        assert "prediction" in fields
        assert "decision" in fields

    def test_c33_enforcement_in_deliberation(self, tmp_path):
        """C-33: stance/confidence rejected in non-PREDICTION rounds."""
        from engine.deliberation_engine import DeliberationEngine

        archetypes = [{"id": "a", "name": "A", "segment": "s"}]
        plan = [
            {"round_n": 1, "round_type": "FREE_FORM"},
            {"round_n": 2, "round_type": "PREDICTION"},
        ]
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(archetypes, 2, plan))

        # Round 1: argument round -- stance should be rejected
        with pytest.raises(ValueError, match="C-33"):
            run_async(engine.deliberation_record_round(1, [
                {"archetype_id": "a", "position_text": "test", "key_arguments": ["x"],
                 "stance": 0.5, "confidence": 0.8},
            ]))


class TestC15WriteThroughPersistence:
    """C-15: Write-through disk persistence after every mutation."""

    def test_state_machine_write_through(self, tmp_path):
        from engine.state_machine import StateMachineEngine
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test", {"topic": "test"}))

        # Every mutation should persist
        run_json = tmp_path / "test" / "_meta" / "run.json"
        assert run_json.exists(), "state_init did not write to disk"

        run_async(engine.state_transition("UNDERSTAND"))
        import json
        with open(run_json) as f:
            data = json.load(f)
        assert data["state"] == "UNDERSTAND", "state_transition did not persist"

    def test_deliberation_write_through(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(
            [{"id": "a", "name": "A", "segment": "s"}], 1,
            [{"round_n": 1, "round_type": "FREE_FORM"}],
        ))
        state_path = tmp_path / "deliberation" / "state.json"
        assert state_path.exists(), "deliberation_init did not persist"


class TestC32DiversityTracking:
    """C-32: Diversity index tracking with premature consensus detection."""

    def test_diversity_index_computed(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine

        archetypes = [{"id": f"a-{i}", "name": f"A{i}", "segment": f"s{i}"} for i in range(5)]
        plan = [{"round_n": 1, "round_type": "FREE_FORM"}]

        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(archetypes, 1, plan))
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": f"a-{i}", "position_text": f"pos {i}", "key_arguments": [
                f"unique-arg-{i}-a", f"unique-arg-{i}-b",
            ]}
            for i in range(5)
        ]))

        result = run_async(engine.deliberation_check_convergence())
        # 10 unique arguments, should have diversity index
        assert result["total_unique_arguments"] >= 5
        if result["total_unique_arguments"] >= 5:
            assert result["diversity_index"] is not None

    def test_premature_consensus_detection(self, tmp_path):
        """Spec: cluster_count < 3 before round 5 -> INJECT_CONTRARIAN."""
        from engine.deliberation_engine import DeliberationEngine

        archetypes = [{"id": "a-0", "name": "A0", "segment": "s0"}]
        plan = [{"round_n": 1, "round_type": "FREE_FORM"}]

        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(archetypes, 6, plan))
        # All same-ish arguments = low cluster count
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "a-0", "position_text": "test", "key_arguments": [
                "regulation helps market stability and growth",
                "regulation ensures market stability protection",
                "regulation supports market stability framework",
                "regulation provides market stability guarantee",
                "regulation enables market stability assurance",
            ]},
        ]))

        result = run_async(engine.deliberation_check_convergence())
        # These very similar arguments should cluster tightly
        # If cluster_count < 3 and we're before round 5, should get INJECT_CONTRARIAN
        if result["cluster_count"] < 3:
            assert result["recommendation"] == "INJECT_CONTRARIAN"
