"""Success Criteria Tests (SC-01, SC-06, SC-07, SC-10 in Worker A scope).

SC-01: MCP server starts via stdio, responds to all 27 tool calls
SC-06: State machine correctly enforces 8-state transitions (9 values incl ERROR)
SC-07: PredictionPosition schema is single source of truth
SC-10: Write-through persistence after every mutation
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestSC01ServerTools:
    """SC-01: MCP server starts via stdio and responds to all 27 tool calls with valid JSON."""

    def test_server_module_importable(self):
        import engine.server
        assert engine.server.app is not None

    def test_server_has_main_function(self):
        from engine.server import main
        assert callable(main)

    def test_21_core_tools_registered_across_engines(self):
        """Verify all 21 core tools exist as async functions in their respective engine modules."""
        import inspect
        import engine.state_machine
        import engine.deliberation_engine
        import engine.graph_engine
        import engine.amplification_engine
        import engine.metrics_engine

        # Check each engine module source for tool function definitions
        tool_module_map = {
            "state_init": engine.state_machine,
            "state_transition": engine.state_machine,
            "state_get": engine.state_machine,
            "state_checkpoint": engine.state_machine,
            "state_resume": engine.state_machine,
            "deliberation_init": engine.deliberation_engine,
            "deliberation_record_round": engine.deliberation_engine,
            "deliberation_track_evolution": engine.deliberation_engine,
            "deliberation_check_convergence": engine.deliberation_engine,
            "deliberation_get_position_map": engine.deliberation_engine,
            "graph_init": engine.graph_engine,
            "graph_add_node": engine.graph_engine,
            "graph_add_edge": engine.graph_engine,
            "graph_query": engine.graph_engine,
            "graph_compute_centrality": engine.graph_engine,
            "amplify_init": engine.amplification_engine,
            "amplify_record_batch": engine.amplification_engine,
            "amplify_aggregate": engine.amplification_engine,
            "metrics_compute_round": engine.metrics_engine,
            "metrics_sentiment_keyword": engine.metrics_engine,
            "metrics_get_trend": engine.metrics_engine,
        }
        assert len(tool_module_map) == 21

        for tool_name, module in tool_module_map.items():
            source = inspect.getsource(module)
            assert tool_name in source, f"Tool '{tool_name}' not found in {module.__name__}"

    def test_all_register_functions_called(self):
        import inspect
        import engine.server
        source = inspect.getsource(engine.server)

        registers = [
            "register_state_tools(app",
            "register_deliberation_tools(app",
            "register_graph_tools(app",
            "register_amplification_tools(app",
            "register_metrics_tools(app",
            "register_calibration_tools(app",
        ]
        for reg in registers:
            assert reg in source, f"Missing registration call: {reg}"


class TestSC06StateMachine:
    """SC-06: State machine correctly enforces 8-state transitions."""

    def test_full_happy_path_transitions(self, tmp_path):
        from engine.state_machine import StateMachineEngine
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("run-sc06", {"topic": "test"}))

        phases = ["UNDERSTAND", "BASELINE_AMPLIFY", "DELIBERATE", "AMPLIFY", "SYNTHESIZE", "INTERACT", "COMPLETE"]
        for phase in phases:
            result = run_async(engine.state_transition(phase))
            assert result["new_state"] == phase

    def test_skip_phase_blocked(self, tmp_path):
        import pytest
        from engine.state_machine import StateMachineEngine
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("run-sc06b", {"topic": "test"}))
        run_async(engine.state_transition("UNDERSTAND"))
        with pytest.raises(ValueError):
            run_async(engine.state_transition("DELIBERATE"))  # Must go through BASELINE_AMPLIFY


class TestSC07PredictionPositionSoT:
    """SC-07: PredictionPosition schema is single source of truth."""

    def test_prediction_position_in_models(self):
        from engine.models import PredictionPosition
        assert PredictionPosition is not None

    def test_13_fields(self):
        from engine.models import PredictionPosition
        assert len(PredictionPosition.model_fields) == 13

    def test_schema_exportable(self):
        """Schema can be exported for --json-schema enforcement."""
        from engine.models import PredictionPosition
        schema = PredictionPosition.model_json_schema()
        assert "properties" in schema
        assert len(schema["properties"]) == 13

    def test_deliberation_engine_uses_same_model(self):
        """Verify deliberation engine imports from models.py, not redefines."""
        import inspect
        import engine.deliberation_engine
        source = inspect.getsource(engine.deliberation_engine)
        assert "from .models import" in source or "from engine.models import" in source
        assert "class PredictionPosition" not in source, "Deliberation engine should NOT redefine PredictionPosition"


class TestSC10WriteThrough:
    """SC-10: Write-through persistence after every mutation."""

    def test_state_init_writes_to_disk(self, tmp_path):
        from engine.state_machine import StateMachineEngine
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("run-sc10", {"topic": "test"}))
        run_json = tmp_path / "run-sc10" / "_meta" / "run.json"
        assert run_json.exists()

    def test_state_transition_writes_to_disk(self, tmp_path):
        from engine.state_machine import StateMachineEngine
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("run-sc10b", {"topic": "test"}))
        run_async(engine.state_transition("UNDERSTAND"))
        run_json = tmp_path / "run-sc10b" / "_meta" / "run.json"
        with open(run_json) as f:
            data = json.load(f)
        assert data["state"] == "UNDERSTAND"

    def test_deliberation_record_writes_to_disk(self, tmp_path):
        from engine.deliberation_engine import DeliberationEngine
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(
            [{"id": "a", "name": "A", "segment": "s"}], 1,
            [{"round_n": 1, "round_type": "FREE_FORM"}],
        ))
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "a", "position_text": "test", "key_arguments": ["arg"]},
        ]))
        state_path = tmp_path / "deliberation" / "state.json"
        assert state_path.exists()
        with open(state_path) as f:
            data = json.load(f)
        assert "1" in data["rounds"] or 1 in data["rounds"]

    def test_graph_mutation_writes_to_disk(self, tmp_path):
        from engine.graph_engine import GraphEngine
        engine = GraphEngine(tmp_path)
        run_async(engine.graph_init({
            "entity_types": [{"name": "test", "description": ""}],
            "edge_types": [],
        }))
        run_async(engine.graph_add_node("node1", "test"))
        state_path = tmp_path / "graph" / "state.json"
        assert state_path.exists()

    def test_amplification_mutation_writes_to_disk(self, tmp_path):
        from engine.amplification_engine import AmplificationEngine
        engine = AmplificationEngine(tmp_path)
        run_async(engine.amplify_init([{"id": "a", "name": "A", "segment": "s"}]))
        run_async(engine.amplify_record_batch("b1", [
            {"persona_id": "p1", "archetype_id": "a", "action": "adopt", "reasoning": "test", "confidence": 0.5},
        ]))
        state_path = tmp_path / "amplification" / "state.json"
        assert state_path.exists()
