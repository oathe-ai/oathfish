"""Hazard mitigation attack tests for Worker A.

A-H01: Position type discrimination via round plan
A-H02: Atomic write-through via temp+rename
A-H06: Diversity index null when < 5 arguments
A-H07: Pagination parameters on large-output tools
A-H11: Round 6 evolution uses absolute values
A-H12: Uses CLAUDE_PLUGIN_DATA not CLAUDE_PLUGIN_ROOT
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

import pytest


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestAH01PositionTypeDiscrimination:
    """A-H01: Type discrimination via round plan (RoundType enum), not hardcoded round 6."""

    def test_round_2_can_be_prediction_if_plan_says_so(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine

        archetypes = [{"id": "arch-0", "name": "Test", "segment": "test"}]
        custom_plan = [
            {"round_n": 1, "round_type": "FREE_FORM"},
            {"round_n": 2, "round_type": "PREDICTION"},  # PREDICTION at round 2!
        ]

        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(archetypes, 2, custom_plan))
        result = run_async(engine.deliberation_record_round(2, [
            {"archetype_id": "arch-0", "prediction": "Early", "decision": "adopt", "stance": 0.5, "confidence": 0.7},
        ]))
        assert result["round_type"] == "prediction"

    def test_round_6_can_be_argument_if_plan_says_so(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine

        archetypes = [{"id": "arch-0", "name": "Test", "segment": "test"}]
        custom_plan = [
            {"round_n": 1, "round_type": "FREE_FORM"},
            {"round_n": 6, "round_type": "FREE_FORM"},  # Round 6 is FREE_FORM!
        ]

        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(archetypes, 6, custom_plan))
        result = run_async(engine.deliberation_record_round(6, [
            {"archetype_id": "arch-0", "position_text": "Still arguing", "key_arguments": ["arg1"]},
        ]))
        assert result["round_type"] == "argument"


class TestAH02AtomicWrite:
    """A-H02: Atomic write via temp+rename, os.fsync()."""

    def test_concurrent_writes_no_corruption(self, tmp_path):
        """Simulate rapid successive writes -- no partial writes."""
        from engine.persistence import atomic_write_json, read_json

        target = tmp_path / "concurrent.json"
        for i in range(100):
            atomic_write_json(target, {"version": i, "data": "x" * 1000})

        result = read_json(target)
        assert result["version"] == 99
        assert len(result["data"]) == 1000

    def test_original_intact_on_failure(self, tmp_path):
        from engine.persistence import atomic_write_json, read_json
        from unittest.mock import patch

        target = tmp_path / "safe.json"
        original = {"critical": True, "version": 1}
        atomic_write_json(target, original)

        # Simulate write failure
        with patch("engine.persistence.os.replace", side_effect=OSError("disk full")):
            try:
                atomic_write_json(target, {"corrupted": True})
            except OSError:
                pass

        loaded = read_json(target)
        assert loaded == original


class TestAH06DiversityIndexLowN:
    """A-H06: Diversity index null when total_unique_arguments < 5 with INSUFFICIENT_DATA flag."""

    def test_diversity_null_with_1_argument(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine

        archetypes = [{"id": "arch-0", "name": "Test", "segment": "test"}]
        plan = [{"round_n": 1, "round_type": "FREE_FORM"}]

        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(archetypes, 1, plan))
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "test", "key_arguments": ["only-one"]},
        ]))
        result = run_async(engine.deliberation_check_convergence())
        assert result["diversity_index"] is None
        assert result["diversity_flag"] == "INSUFFICIENT_DATA"
        assert result["total_unique_arguments"] < 5

    def test_diversity_null_with_4_arguments(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine

        archetypes = [{"id": "arch-0", "name": "Test", "segment": "test"}]
        plan = [{"round_n": 1, "round_type": "FREE_FORM"}]

        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(archetypes, 1, plan))
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "test", "key_arguments": ["a", "b", "c", "d"]},
        ]))
        result = run_async(engine.deliberation_check_convergence())
        assert result["diversity_index"] is None
        assert result["diversity_flag"] == "INSUFFICIENT_DATA"

    def test_diversity_present_with_5_or_more(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine

        archetypes = [{"id": "arch-0", "name": "Test", "segment": "test"}]
        plan = [{"round_n": 1, "round_type": "FREE_FORM"}]

        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(archetypes, 1, plan))
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "test", "key_arguments": [
                "regulation stabilizes markets",
                "technology disrupts industries",
                "competition drives innovation",
                "policy shapes behavior patterns",
                "economics governs investment decisions",
            ]},
        ]))
        result = run_async(engine.deliberation_check_convergence())
        assert result["diversity_index"] is not None
        assert result["diversity_flag"] == ""


class TestAH07Pagination:
    """A-H07: Pagination parameters on large-output tools."""

    def test_position_map_archetype_filter(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine

        archetypes = [{"id": f"arch-{i}", "name": f"A{i}", "segment": f"s{i}"} for i in range(30)]
        plan = [{"round_n": 1, "round_type": "FREE_FORM"}]

        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(archetypes, 1, plan))
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": f"arch-{i}", "position_text": f"pos {i}", "key_arguments": [f"arg-{i}"]}
            for i in range(30)
        ]))

        # Paginate: only get 3 archetypes
        result = run_async(engine.deliberation_get_position_map(archetype_ids=["arch-0", "arch-1", "arch-2"]))
        assert len(result["archetypes"]) == 3

    def test_graph_max_results(self, tmp_path):
        from engine.graph_engine import GraphEngine

        ontology = {
            "entity_types": [{"name": "node", "description": ""}],
            "edge_types": [{"name": "link", "description": ""}],
        }
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(ontology))
        center = run_async(engine.graph_add_node("center", "node"))
        for i in range(20):
            n = run_async(engine.graph_add_node(f"n-{i}", "node"))
            run_async(engine.graph_add_edge(center["node_id"], n["node_id"], "link"))

        result = run_async(engine.graph_query(center["node_id"], max_results=5))
        assert len(result["edges"]) <= 5

    def test_amplification_archetype_filter(self, tmp_path):
        from engine.amplification_engine import AmplificationEngine

        archetypes = [{"id": f"arch-{i}", "name": f"A{i}", "segment": f"s{i}"} for i in range(10)]
        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init(archetypes))
        run_async(engine.amplify_record_batch("b1", [
            {"persona_id": f"p-{i}", "archetype_id": f"arch-{i % 10}", "action": "adopt", "reasoning": "test", "confidence": 0.5}
            for i in range(50)
        ]))
        result = run_async(engine.amplify_aggregate(archetype_ids=["arch-0"]))
        assert len(result["per_archetype"]) == 1


class TestAH11Round6EvolutionAbsolute:
    """A-H11: Round 6 evolution stores absolute values (not deltas vs round 5)."""

    def test_prediction_evolution_is_absolute(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine

        archetypes = [{"id": "arch-0", "name": "Test", "segment": "test"}]
        plan = [
            {"round_n": 1, "round_type": "FREE_FORM"},
            {"round_n": 6, "round_type": "PREDICTION"},
        ]

        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(archetypes, 6, plan))
        run_async(engine.deliberation_record_round(6, [
            {"archetype_id": "arch-0", "prediction": "Adopt", "decision": "adopt", "stance": 0.65, "confidence": 0.82},
        ]))

        result = run_async(engine.deliberation_track_evolution(6))
        evo = result["evolutions"][0]
        # These must be ABSOLUTE values matching what was recorded
        assert evo["stance"] == 0.65
        assert evo["confidence"] == 0.82


class TestAH12DataDirEnvVar:
    """A-H12: Uses CLAUDE_PLUGIN_DATA not CLAUDE_PLUGIN_ROOT."""

    def test_server_uses_oathfish_data_dir(self):
        import inspect
        import engine.server
        source = inspect.getsource(engine.server)
        assert "OATHFISH_DATA_DIR" in source
        # Must NOT use CLAUDE_PLUGIN_ROOT as the data dir
        lines = source.split("\n")
        for line in lines:
            if "os.environ.get" in line and "CLAUDE_PLUGIN_ROOT" in line:
                assert False, f"Server reads CLAUDE_PLUGIN_ROOT as data dir: {line}"
