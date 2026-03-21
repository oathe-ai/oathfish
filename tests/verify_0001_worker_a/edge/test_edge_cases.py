"""Edge case tests for Worker A components.

Tests unusual inputs, boundary conditions, and error handling.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

import pytest


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestModelsEdgeCases:
    def test_prediction_position_stance_at_boundaries(self):
        from engine.models import PredictionPosition
        # Exact boundary values
        pos_min = PredictionPosition(
            archetype_id="t", round_n=6, prediction="p",
            decision="d", stance=-1.0, confidence=0.0,
        )
        assert pos_min.stance == -1.0
        assert pos_min.confidence == 0.0

        pos_max = PredictionPosition(
            archetype_id="t", round_n=6, prediction="p",
            decision="d", stance=1.0, confidence=1.0,
        )
        assert pos_max.stance == 1.0
        assert pos_max.confidence == 1.0

    def test_prediction_position_rejects_stance_over_1(self):
        from engine.models import PredictionPosition
        with pytest.raises(Exception):
            PredictionPosition(
                archetype_id="t", round_n=6, prediction="p",
                decision="d", stance=1.01, confidence=0.5,
            )

    def test_prediction_position_rejects_stance_under_neg1(self):
        from engine.models import PredictionPosition
        with pytest.raises(Exception):
            PredictionPosition(
                archetype_id="t", round_n=6, prediction="p",
                decision="d", stance=-1.01, confidence=0.5,
            )

    def test_empty_key_arguments(self):
        from engine.models import ArgumentPosition
        pos = ArgumentPosition(
            archetype_id="t", round_n=1,
            position_text="test", key_arguments=[],
        )
        assert pos.key_arguments == []

    def test_archetype_minimal_construction(self):
        from engine.models import Archetype
        arch = Archetype(id="min", name="Min", segment="s")
        assert arch.id == "min"
        assert arch.grounding_sources == []
        assert arch.is_structural is False

    def test_run_config_defaults(self):
        from engine.models import RunConfig
        config = RunConfig(topic="test")
        assert config.archetype_count == 30
        assert config.deliberation_rounds == 6
        assert config.amplification_per_archetype == 50


class TestStateMachineEdgeCases:
    def test_state_get_before_init(self, tmp_path):
        from engine.state_machine import StateMachineEngine
        engine = StateMachineEngine(tmp_path)
        result = run_async(engine.state_get())
        assert result["state"] is None

    def test_transition_before_init(self, tmp_path):
        from engine.state_machine import StateMachineEngine
        engine = StateMachineEngine(tmp_path)
        with pytest.raises(ValueError, match="No active run"):
            run_async(engine.state_transition("UNDERSTAND"))

    def test_checkpoint_before_init(self, tmp_path):
        from engine.state_machine import StateMachineEngine
        engine = StateMachineEngine(tmp_path)
        with pytest.raises(ValueError, match="No active run"):
            run_async(engine.state_checkpoint("INIT", {}))

    def test_resume_empty_directory(self, tmp_path):
        from engine.state_machine import StateMachineEngine
        engine = StateMachineEngine(tmp_path)
        result = run_async(engine.state_resume())
        assert result["state"] is None

    def test_invalid_state_string(self, tmp_path):
        from engine.state_machine import StateMachineEngine
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test", {"topic": "test"}))
        with pytest.raises(ValueError):
            run_async(engine.state_transition("INVALID_STATE"))


class TestDeliberationEdgeCases:
    def test_record_round_before_init(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine
        engine = DeliberationEngine(tmp_path)
        with pytest.raises(ValueError, match="No active deliberation"):
            run_async(engine.deliberation_record_round(1, []))

    def test_evolution_before_init(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine
        engine = DeliberationEngine(tmp_path)
        with pytest.raises(ValueError, match="No active deliberation"):
            run_async(engine.deliberation_track_evolution(1))

    def test_convergence_before_init(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine
        engine = DeliberationEngine(tmp_path)
        with pytest.raises(ValueError, match="No active deliberation"):
            run_async(engine.deliberation_check_convergence())

    def test_position_map_before_init(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine
        engine = DeliberationEngine(tmp_path)
        with pytest.raises(ValueError, match="No active deliberation"):
            run_async(engine.deliberation_get_position_map())

    def test_record_round_not_in_plan(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine
        archetypes = [{"id": "a", "name": "A", "segment": "s"}]
        plan = [{"round_n": 1, "round_type": "FREE_FORM"}]
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(archetypes, 1, plan))
        with pytest.raises(ValueError, match="not in round plan"):
            run_async(engine.deliberation_record_round(99, []))


class TestGraphEdgeCases:
    def test_operations_before_init(self, tmp_path):
        from engine.graph_engine import GraphEngine
        engine = GraphEngine(tmp_path)
        with pytest.raises(ValueError, match="No active graph"):
            run_async(engine.graph_add_node("test", "test"))

    def test_query_nonexistent_node(self, tmp_path):
        from engine.graph_engine import GraphEngine
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init({
            "entity_types": [{"name": "test", "description": ""}],
            "edge_types": [],
        }))
        result = run_async(engine.graph_query("nonexistent"))
        assert "error" in result

    def test_centrality_empty_graph(self, tmp_path):
        from engine.graph_engine import GraphEngine
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init({
            "entity_types": [{"name": "test", "description": ""}],
            "edge_types": [],
        }))
        result = run_async(engine.graph_compute_centrality())
        assert result["rankings"] == []


class TestAmplificationEdgeCases:
    def test_aggregate_before_init(self, tmp_path):
        from engine.amplification_engine import AmplificationEngine
        engine = AmplificationEngine(tmp_path)
        with pytest.raises(ValueError, match="No active amplification"):
            run_async(engine.amplify_aggregate())

    def test_aggregate_empty_batches(self, tmp_path):
        from engine.amplification_engine import AmplificationEngine
        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init([{"id": "a", "name": "A", "segment": "s"}]))
        result = run_async(engine.amplify_aggregate())
        assert result["per_archetype"] == []

    def test_record_batch_before_init(self, tmp_path):
        from engine.amplification_engine import AmplificationEngine
        engine = AmplificationEngine(tmp_path)
        with pytest.raises(ValueError, match="No active amplification"):
            run_async(engine.amplify_record_batch("b1", []))


class TestSentimentEdgeCases:
    def test_single_word_positive(self):
        from engine.sentiment import compute_sentiment
        result = compute_sentiment("excellent")
        assert result.score > 0

    def test_single_word_negative(self):
        from engine.sentiment import compute_sentiment
        result = compute_sentiment("terrible")
        assert result.score < 0

    def test_very_long_text(self):
        from engine.sentiment import compute_sentiment
        text = "great " * 10000
        result = compute_sentiment(text)
        assert result.score > 0

    def test_special_characters(self):
        from engine.sentiment import compute_sentiment
        result = compute_sentiment("!@#$%^&*() {} [] <> ???")
        assert result.score == 0.0

    def test_mixed_case(self):
        from engine.sentiment import compute_sentiment
        r1 = compute_sentiment("EXCELLENT")
        r2 = compute_sentiment("excellent")
        assert r1.score == r2.score  # Case insensitive


class TestPersistenceEdgeCases:
    def test_read_nonexistent_file(self, tmp_path):
        from engine.persistence import read_json
        result = read_json(tmp_path / "does_not_exist.json")
        assert result is None

    def test_write_to_deep_nonexistent_path(self, tmp_path):
        from engine.persistence import atomic_write_json
        target = tmp_path / "a" / "b" / "c" / "d" / "test.json"
        atomic_write_json(target, {"deep": True})
        assert target.exists()

    def test_write_large_data(self, tmp_path):
        from engine.persistence import atomic_write_json, read_json
        target = tmp_path / "large.json"
        data = {"items": [{"id": i, "data": "x" * 100} for i in range(1000)]}
        atomic_write_json(target, data)
        loaded = read_json(target)
        assert len(loaded["items"]) == 1000
