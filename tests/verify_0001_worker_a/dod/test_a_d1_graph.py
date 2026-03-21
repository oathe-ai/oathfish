"""DoD A-D.1: engine/graph_engine.py -- CRUD; temporal queries exclude expired edges.

Spec claims:
- graph_init, graph_add_node, graph_add_edge, graph_query, graph_compute_centrality (but actual names may differ)
- Temporal filtering via as_of parameter
- max_results pagination
- Write-through persistence
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

import pytest
from engine.graph_engine import GraphEngine


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


SAMPLE_ONTOLOGY = {
    "entity_types": [
        {"name": "archetype", "description": "An archetype agent"},
        {"name": "argument", "description": "A deliberation argument"},
    ],
    "edge_types": [
        {"name": "supports", "description": "Supports an argument"},
        {"name": "opposes", "description": "Opposes an argument"},
    ],
}


class TestGraphInit:
    def test_creates_graph(self, tmp_path):
        engine = GraphEngine(tmp_path)
        result = run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        assert "graph_id" in result
        assert result["entity_types_count"] == 2
        assert result["edge_types_count"] == 2

    def test_persists_to_disk(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        state_path = tmp_path / "graph" / "state.json"
        assert state_path.exists()


class TestGraphCRUD:
    """Spec: CRUD operations work."""

    def test_add_node(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        result = run_async(engine.graph_add_node("historian", "archetype", "Historical lens"))
        assert "node_id" in result
        assert result["name"] == "historian"

    def test_add_node_invalid_type_rejected(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        with pytest.raises(ValueError, match="not in ontology"):
            run_async(engine.graph_add_node("test", "invalid_type"))

    def test_add_edge(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        n1 = run_async(engine.graph_add_node("historian", "archetype"))
        n2 = run_async(engine.graph_add_node("regulation-arg", "argument"))
        result = run_async(engine.graph_add_edge(
            n1["node_id"], n2["node_id"], "supports",
            facts="Historian supports regulation based on historical precedent",
        ))
        assert "edge_id" in result
        assert result["type"] == "supports"

    def test_add_edge_invalid_type_rejected(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        n1 = run_async(engine.graph_add_node("historian", "archetype"))
        n2 = run_async(engine.graph_add_node("arg", "argument"))
        with pytest.raises(ValueError, match="not in ontology"):
            run_async(engine.graph_add_edge(n1["node_id"], n2["node_id"], "invalid_edge"))

    def test_add_edge_invalid_node_rejected(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        with pytest.raises(ValueError, match="Node not found"):
            run_async(engine.graph_add_edge("nonexistent", "also-nonexistent", "supports"))

    def test_query_node(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        n1 = run_async(engine.graph_add_node("historian", "archetype"))
        n2 = run_async(engine.graph_add_node("arg1", "argument"))
        run_async(engine.graph_add_edge(n1["node_id"], n2["node_id"], "supports"))
        result = run_async(engine.graph_query(n1["node_id"]))
        assert result["node"]["name"] == "historian"
        assert len(result["edges"]) == 1

    def test_query_by_name(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        run_async(engine.graph_add_node("historian", "archetype"))
        result = run_async(engine.graph_query("historian"))
        assert result["node"]["name"] == "historian"

    def test_query_nonexistent_returns_error(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        result = run_async(engine.graph_query("nonexistent"))
        assert "error" in result


class TestTemporalFiltering:
    """Spec A-H04: Temporal queries exclude expired edges."""

    def test_expired_edge_excluded(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        n1 = run_async(engine.graph_add_node("historian", "archetype"))
        n2 = run_async(engine.graph_add_node("arg1", "argument"))
        # Edge valid from round-1 to round-3 (expired at round-3)
        run_async(engine.graph_add_edge(
            n1["node_id"], n2["node_id"], "supports",
            valid_at="round-1", invalid_at="round-3",
        ))
        # Query at round-4: edge should be excluded
        result = run_async(engine.graph_query(n1["node_id"], as_of="round-4"))
        assert len(result["edges"]) == 0, "Expired edge should be excluded"

    def test_valid_edge_included(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        n1 = run_async(engine.graph_add_node("historian", "archetype"))
        n2 = run_async(engine.graph_add_node("arg1", "argument"))
        run_async(engine.graph_add_edge(
            n1["node_id"], n2["node_id"], "supports",
            valid_at="round-1", invalid_at="round-5",
        ))
        # Query at round-2: edge should be included
        result = run_async(engine.graph_query(n1["node_id"], as_of="round-2"))
        assert len(result["edges"]) == 1

    def test_no_temporal_filter_returns_all(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        n1 = run_async(engine.graph_add_node("historian", "archetype"))
        n2 = run_async(engine.graph_add_node("arg1", "argument"))
        run_async(engine.graph_add_edge(
            n1["node_id"], n2["node_id"], "supports",
            valid_at="round-1", invalid_at="round-3",
        ))
        # No as_of filter: all edges returned
        result = run_async(engine.graph_query(n1["node_id"]))
        assert len(result["edges"]) == 1


class TestPagination:
    """Spec A-H07: max_results pagination."""

    def test_max_results_limits_output(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        center = run_async(engine.graph_add_node("center", "archetype"))
        # Add many edges
        for i in range(10):
            n = run_async(engine.graph_add_node(f"arg-{i}", "argument"))
            run_async(engine.graph_add_edge(center["node_id"], n["node_id"], "supports"))

        result = run_async(engine.graph_query(center["node_id"], max_results=3))
        assert len(result["edges"]) <= 3


class TestCentrality:
    def test_centrality_ranking(self, tmp_path):
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init(SAMPLE_ONTOLOGY))
        n1 = run_async(engine.graph_add_node("hub", "archetype"))
        n2 = run_async(engine.graph_add_node("spoke1", "argument"))
        n3 = run_async(engine.graph_add_node("spoke2", "argument"))
        run_async(engine.graph_add_edge(n1["node_id"], n2["node_id"], "supports"))
        run_async(engine.graph_add_edge(n1["node_id"], n3["node_id"], "supports"))
        result = run_async(engine.graph_compute_centrality())
        rankings = result["rankings"]
        # Hub should be rank 1 (most connections)
        assert rankings[0]["name"] == "hub"
        assert rankings[0]["degree"] == 2
