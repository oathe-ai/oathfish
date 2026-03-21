"""Integration: End-to-end happy path through all Worker A engines.

Simulates: INIT -> create state -> init deliberation -> record rounds -> track evolution
-> check convergence -> init graph -> CRUD graph -> init amplification -> record batch
-> aggregate -> compute metrics -> sentiment analysis -> get trend.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestE2EHappyPath:
    """Full pipeline through all Worker A engines."""

    def test_full_pipeline(self, tmp_path):
        from engine.state_machine import StateMachineEngine
        from engine.deliberation_engine import DeliberationEngine
        from engine.graph_engine import GraphEngine
        from engine.amplification_engine import AmplificationEngine
        from engine.metrics_engine import MetricsEngine

        data_dir = tmp_path

        # --- STATE MACHINE ---
        sm = StateMachineEngine(data_dir)
        result = run_async(sm.state_init("run-e2e", {"topic": "AI regulation impact on startups"}))
        assert result["state"] == "INIT"
        run_async(sm.state_transition("UNDERSTAND"))
        run_async(sm.state_transition("BASELINE_AMPLIFY"))

        # --- AMPLIFICATION (baseline) ---
        amp = AmplificationEngine(data_dir)
        run_async(amp.amplify_init(
            [{"id": "arch-0", "name": "Historian", "segment": "structural"}],
            variations_per_archetype=10, is_baseline=True,
        ))
        run_async(amp.amplify_record_batch("baseline-1", [
            {"persona_id": f"p-{i}", "archetype_id": "arch-0", "action": "adopt",
             "reasoning": "Historical precedent shows adoption", "confidence": 0.7}
            for i in range(10)
        ]))
        agg_baseline = run_async(amp.amplify_aggregate())
        assert agg_baseline["overall"]["total_results"] == 10

        # --- DELIBERATION ---
        run_async(sm.state_transition("DELIBERATE"))

        archetypes = [
            {"id": "arch-hist", "name": "Historian", "segment": "structural"},
            {"id": "arch-contra", "name": "Contrarian", "segment": "structural"},
            {"id": "arch-prob", "name": "Probabilist", "segment": "structural"},
        ]
        round_plan = [
            {"round_n": 1, "round_type": "FREE_FORM"},
            {"round_n": 2, "round_type": "FREE_FORM"},
            {"round_n": 3, "round_type": "STRUCTURED_DEBATE"},
            {"round_n": 4, "round_type": "SCENARIO_REACTION"},
            {"round_n": 5, "round_type": "SCENARIO_REACTION"},
            {"round_n": 6, "round_type": "PREDICTION"},
        ]

        delib = DeliberationEngine(data_dir)
        delib_result = run_async(delib.deliberation_init(archetypes, 6, round_plan))
        assert delib_result["archetype_count"] == 3

        # Round 1: FREE_FORM arguments
        run_async(delib.deliberation_record_round(1, [
            {"archetype_id": "arch-hist", "position_text": "Historical analysis suggests caution",
             "key_arguments": ["precedent shows slow adoption", "regulatory burden increases costs"]},
            {"archetype_id": "arch-contra", "position_text": "Regulation will accelerate innovation",
             "key_arguments": ["clear rules enable investment", "reduces uncertainty"]},
            {"archetype_id": "arch-prob", "position_text": "Probability favors mixed outcomes",
             "key_arguments": ["base rate for regulation impact is 60% neutral", "sector-dependent effects"]},
        ]))

        # Round 2: more arguments
        run_async(delib.deliberation_record_round(2, [
            {"archetype_id": "arch-hist", "position_text": "Updated position with new evidence",
             "key_arguments": ["precedent shows slow adoption", "compliance cost data from EU"],
             "influenced_by": ["arch-contra"]},
            {"archetype_id": "arch-contra", "position_text": "Maintain contrarian view",
             "key_arguments": ["clear rules enable investment", "first-mover advantage for compliant startups"]},
            {"archetype_id": "arch-prob", "position_text": "Bayesian update",
             "key_arguments": ["base rate updated to 55% neutral", "sector-dependent effects", "time horizon matters"]},
        ]))

        # Track evolution
        evo_result = run_async(delib.deliberation_track_evolution(2))
        assert len(evo_result["evolutions"]) == 3

        # Check convergence
        conv_result = run_async(delib.deliberation_check_convergence())
        assert "diversity_index" in conv_result
        assert "recommendation" in conv_result

        # Round 6: PREDICTION
        run_async(delib.deliberation_record_round(6, [
            {"archetype_id": "arch-hist", "prediction": "Cautious adoption",
             "decision": "wait", "stance": -0.3, "confidence": 0.75,
             "timeframe": "2-3 years", "base_rate_anchor": "EU GDPR adoption curve",
             "key_uncertainties": ["enforcement timeline"], "falsification_criteria": "If > 50% adopt within 1 year",
             "second_order_effects": ["compliance industry growth"], "cascade_susceptibility": 0.4,
             "coalition_alignment": ["arch-prob"]},
            {"archetype_id": "arch-contra", "prediction": "Rapid adoption by compliant startups",
             "decision": "adopt", "stance": 0.7, "confidence": 0.85,
             "coalition_alignment": []},
            {"archetype_id": "arch-prob", "prediction": "Mixed with sector variation",
             "decision": "mixed", "stance": 0.1, "confidence": 0.65,
             "coalition_alignment": ["arch-hist"]},
        ]))

        # Position map
        pos_map = run_async(delib.deliberation_get_position_map(detail_level="full"))
        assert len(pos_map["archetypes"]) == 3

        # --- GRAPH ---
        graph = GraphEngine(data_dir)
        run_async(graph.graph_init({
            "entity_types": [
                {"name": "archetype", "description": "Deliberation archetype"},
                {"name": "argument", "description": "Key argument"},
            ],
            "edge_types": [
                {"name": "supports", "description": "Supports argument"},
                {"name": "opposes", "description": "Opposes argument"},
                {"name": "influences", "description": "Influences another"},
            ],
        }))
        n_hist = run_async(graph.graph_add_node("Historian", "archetype"))
        n_arg = run_async(graph.graph_add_node("regulation-caution", "argument"))
        run_async(graph.graph_add_edge(n_hist["node_id"], n_arg["node_id"], "supports"))

        centrality = run_async(graph.graph_compute_centrality())
        assert len(centrality["rankings"]) == 2

        # --- AMPLIFICATION (informed) ---
        run_async(sm.state_transition("AMPLIFY"))

        amp2 = AmplificationEngine(data_dir)
        run_async(amp2.amplify_init(
            [{"id": "arch-hist", "name": "Historian", "segment": "structural"}],
            variations_per_archetype=5, is_baseline=False,
        ))
        run_async(amp2.amplify_record_batch("informed-1", [
            {"persona_id": f"pi-{i}", "archetype_id": "arch-hist", "action": "wait",
             "reasoning": "Informed by deliberation insights", "confidence": 0.6}
            for i in range(5)
        ]))
        agg_informed = run_async(amp2.amplify_aggregate())
        assert agg_informed["overall"]["total_results"] == 5

        # --- METRICS ---
        metrics = MetricsEngine(data_dir)
        round_metrics = run_async(metrics.metrics_compute_round(1))
        assert round_metrics["round_n"] == 1
        assert "engagement" in round_metrics

        sentiment = run_async(metrics.metrics_sentiment_keyword(
            "The regulation will have both positive and negative impacts on innovation"
        ))
        assert "score" in sentiment
        assert "label" in sentiment

        trend = run_async(metrics.metrics_get_trend("engagement"))
        assert trend["metric"] == "engagement"

        # --- COMPLETE ---
        run_async(sm.state_transition("SYNTHESIZE"))
        run_async(sm.state_transition("INTERACT"))
        run_async(sm.state_transition("COMPLETE"))

        final_state = run_async(sm.state_get())
        assert final_state["state"] == "COMPLETE"
        assert len(final_state["state_history"]) == 8  # INIT + 7 transitions

    def test_state_recovery_after_error(self, tmp_path):
        """Error mid-pipeline and recovery."""
        from engine.state_machine import StateMachineEngine

        sm = StateMachineEngine(tmp_path)
        run_async(sm.state_init("run-err", {"topic": "test"}))
        run_async(sm.state_transition("UNDERSTAND"))
        run_async(sm.state_transition("BASELINE_AMPLIFY"))
        run_async(sm.state_transition("ERROR"))

        # Simulate server restart
        sm2 = StateMachineEngine(tmp_path)
        resume = run_async(sm2.state_resume())
        assert resume["state"] == "ERROR"
        assert resume["previous_state"] == "BASELINE_AMPLIFY"

        # Resume
        run_async(sm2.state_transition("BASELINE_AMPLIFY"))
        state = run_async(sm2.state_get())
        assert state["state"] == "BASELINE_AMPLIFY"
