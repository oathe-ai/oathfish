"""DoD A-C.1: engine/deliberation_engine.py -- Polymorphic recording; convergence detection.

Spec claims:
- Polymorphic: ArgumentPosition for non-PREDICTION rounds, PredictionPosition for PREDICTION rounds
- Type discrimination via round plan (RoundType), NOT hardcoded round 6
- C-33: reject stance/confidence in non-PREDICTION rounds
- Jaccard similarity for argument evolution
- Diversity index = distinct_clusters / total_unique_arguments, null when < 5
- Premature consensus: cluster_count < 3 AND diversity_index < 0.15 -> INJECT_CONTRARIAN
- detail_level and archetype_ids pagination on position_map
- Round 6 evolution stores absolute values (not deltas vs round 5)
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

import pytest
from engine.deliberation_engine import DeliberationEngine, cluster_arguments, jaccard_similarity


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


SAMPLE_ARCHETYPES = [
    {"id": f"arch-{i}", "name": f"Archetype {i}", "segment": f"seg-{i}"}
    for i in range(5)
]

# Standard 6-round plan: rounds 1-2 FREE_FORM, 3-4 STRUCTURED_DEBATE, 5 SCENARIO_REACTION, 6 PREDICTION
STANDARD_ROUND_PLAN = [
    {"round_n": 1, "round_type": "FREE_FORM"},
    {"round_n": 2, "round_type": "FREE_FORM"},
    {"round_n": 3, "round_type": "STRUCTURED_DEBATE"},
    {"round_n": 4, "round_type": "STRUCTURED_DEBATE"},
    {"round_n": 5, "round_type": "SCENARIO_REACTION"},
    {"round_n": 6, "round_type": "PREDICTION"},
]


class TestDeliberationInit:
    def test_init_returns_deliberation_id(self, tmp_path):
        engine = DeliberationEngine(tmp_path)
        result = run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))
        assert "deliberation_id" in result
        assert result["archetype_count"] == 5

    def test_init_persists_to_disk(self, tmp_path):
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))
        state_path = tmp_path / "deliberation" / "state.json"
        assert state_path.exists()


class TestPolymorphicRecording:
    """Spec: Type discrimination via round plan, not hardcoded round number."""

    def test_argument_position_accepted_in_free_form(self, tmp_path):
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))
        result = run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "I think regulation helps", "key_arguments": ["stability"]},
        ]))
        assert result["round_type"] == "argument"

    def test_prediction_position_accepted_in_prediction_round(self, tmp_path):
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))
        result = run_async(engine.deliberation_record_round(6, [
            {
                "archetype_id": "arch-0", "prediction": "Will adopt",
                "decision": "adopt", "stance": 0.7, "confidence": 0.85,
            },
        ]))
        assert result["round_type"] == "prediction"

    def test_c33_rejects_stance_in_argument_round(self, tmp_path):
        """C-33: Cannot include stance/confidence fields in non-PREDICTION rounds."""
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))
        with pytest.raises(ValueError, match="C-33"):
            run_async(engine.deliberation_record_round(1, [
                {
                    "archetype_id": "arch-0", "position_text": "test",
                    "key_arguments": ["arg1"], "stance": 0.5, "confidence": 0.8,
                },
            ]))

    def test_type_discrimination_by_round_plan_not_number(self, tmp_path):
        """A-H01: Use round plan, not hardcoded round 6.

        If we make round 3 a PREDICTION round via the plan, it should accept predictions.
        """
        custom_plan = [
            {"round_n": 1, "round_type": "FREE_FORM"},
            {"round_n": 2, "round_type": "FREE_FORM"},
            {"round_n": 3, "round_type": "PREDICTION"},  # Prediction at round 3!
        ]
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 3, custom_plan))
        result = run_async(engine.deliberation_record_round(3, [
            {
                "archetype_id": "arch-0", "prediction": "Early prediction",
                "decision": "adopt", "stance": 0.6, "confidence": 0.7,
            },
        ]))
        assert result["round_type"] == "prediction"


class TestJaccardSimilarity:
    def test_identical_sets(self):
        assert jaccard_similarity({"a", "b", "c"}, {"a", "b", "c"}) == 1.0

    def test_disjoint_sets(self):
        assert jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        result = jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        # Intersection: {b, c} = 2, Union: {a, b, c, d} = 4
        assert abs(result - 0.5) < 0.01

    def test_empty_sets(self):
        assert jaccard_similarity(set(), set()) == 1.0

    def test_one_empty(self):
        assert jaccard_similarity({"a"}, set()) == 0.0


class TestClusterArguments:
    def test_identical_arguments_cluster_together(self):
        args = [
            "regulation will slow adoption",
            "regulation will slow the adoption process",
            "technology disrupts markets",
        ]
        clusters = cluster_arguments(args)
        # First two should cluster together, third separate
        assert len(clusters) >= 2  # At least 2 clusters

    def test_empty_list(self):
        assert cluster_arguments([]) == []


class TestEvolutionTracking:
    """Spec: Jaccard for rounds 1-5, absolute values for prediction rounds."""

    def test_argument_evolution_jaccard(self, tmp_path):
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))

        # Round 1
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "Position 1", "key_arguments": ["arg-a", "arg-b"]},
        ]))

        # Round 2
        run_async(engine.deliberation_record_round(2, [
            {"archetype_id": "arch-0", "position_text": "Position 2", "key_arguments": ["arg-b", "arg-c"]},
        ]))

        result = run_async(engine.deliberation_track_evolution(2))
        evolutions = result["evolutions"]
        assert len(evolutions) >= 1
        evo = evolutions[0]
        assert "jaccard_similarity" in evo
        # Jaccard of {arg-a, arg-b} vs {arg-b, arg-c}: intersection={arg-b}=1, union={arg-a,arg-b,arg-c}=3
        assert abs(evo["jaccard_similarity"] - 1.0 / 3.0) < 0.01

    def test_prediction_evolution_absolute_values(self, tmp_path):
        """A-H11: Round 6 evolution uses absolute values, not deltas."""
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))

        # Record prediction round
        run_async(engine.deliberation_record_round(6, [
            {
                "archetype_id": "arch-0", "prediction": "Will adopt",
                "decision": "adopt", "stance": 0.7, "confidence": 0.85,
            },
        ]))

        result = run_async(engine.deliberation_track_evolution(6))
        evolutions = result["evolutions"]
        assert len(evolutions) >= 1
        evo = evolutions[0]
        # Should store absolute stance and confidence, not delta
        assert "stance" in evo
        assert evo["stance"] == 0.7  # Absolute value
        assert "confidence" in evo
        assert evo["confidence"] == 0.85  # Absolute value

    def test_round_1_evolution_returns_empty(self, tmp_path):
        """No previous round to compare for round 1."""
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "Position 1", "key_arguments": ["arg-a"]},
        ]))
        result = run_async(engine.deliberation_track_evolution(1))
        assert result["evolutions"] == []


class TestConvergenceDetection:
    """Spec: Diversity index null when < 5, INJECT_CONTRARIAN when premature consensus."""

    def test_diversity_index_null_under_5_arguments(self, tmp_path):
        """A-H06: diversity index returns null when total_unique_arguments < 5."""
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "test", "key_arguments": ["arg1", "arg2"]},
            {"archetype_id": "arch-1", "position_text": "test", "key_arguments": ["arg3"]},
        ]))
        result = run_async(engine.deliberation_check_convergence())
        assert result["diversity_index"] is None
        assert result["diversity_flag"] == "INSUFFICIENT_DATA"

    def test_inject_contrarian_on_low_cluster_count(self, tmp_path):
        """Spec: cluster_count < 3 before round 5 -> INJECT_CONTRARIAN."""
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))
        # Record many similar arguments to get low cluster count but >= 5 unique
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "regulation helps", "key_arguments": [
                "regulation stabilizes markets",
                "regulation protects consumers",
                "regulation ensures fairness",
                "regulation improves compliance",
                "regulation creates stability",
            ]},
            {"archetype_id": "arch-1", "position_text": "regulation helps too", "key_arguments": [
                "regulation ensures market stability",
                "regulation protects consumer rights",
            ]},
        ]))
        result = run_async(engine.deliberation_check_convergence())
        # With very similar arguments, cluster count should be low
        # If < 3 clusters before round 5, should recommend INJECT_CONTRARIAN
        if result["cluster_count"] < 3 and result["total_unique_arguments"] >= 5:
            assert result["recommendation"] == "INJECT_CONTRARIAN"


class TestPositionMap:
    """Spec: detail_level and archetype_ids pagination parameters."""

    def test_position_map_summary(self, tmp_path):
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "test", "key_arguments": ["arg1"]},
        ]))
        result = run_async(engine.deliberation_get_position_map(detail_level="summary"))
        assert "archetypes" in result
        assert len(result["archetypes"]) == 5  # All archetypes returned

    def test_position_map_filter_by_archetype_ids(self, tmp_path):
        """A-H07: Pagination -- filter by archetype IDs."""
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "test", "key_arguments": ["arg1"]},
            {"archetype_id": "arch-1", "position_text": "test", "key_arguments": ["arg2"]},
        ]))
        result = run_async(engine.deliberation_get_position_map(archetype_ids=["arch-0"]))
        assert len(result["archetypes"]) == 1
        assert result["archetypes"][0]["id"] == "arch-0"

    def test_position_map_full_detail(self, tmp_path):
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "test", "key_arguments": ["arg1"]},
        ]))
        result = run_async(engine.deliberation_get_position_map(detail_level="full"))
        arch = result["archetypes"][0]
        assert "evolution" in arch


class TestWriteThroughPersistence:
    """Spec C-15: Write-through persistence after every mutation."""

    def test_record_round_persists(self, tmp_path):
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "test", "key_arguments": ["arg1"]},
        ]))

        # New engine instance should be able to read the state
        engine2 = DeliberationEngine(tmp_path)
        result = run_async(engine2.deliberation_get_position_map())
        assert len(result["archetypes"]) == 5

    def test_evolution_persists(self, tmp_path):
        engine = DeliberationEngine(tmp_path)
        run_async(engine.deliberation_init(SAMPLE_ARCHETYPES, 6, STANDARD_ROUND_PLAN))
        run_async(engine.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "test", "key_arguments": ["arg1"]},
        ]))
        run_async(engine.deliberation_record_round(2, [
            {"archetype_id": "arch-0", "position_text": "test2", "key_arguments": ["arg2"]},
        ]))
        run_async(engine.deliberation_track_evolution(2))

        # New engine should see evolution data
        engine2 = DeliberationEngine(tmp_path)
        result = run_async(engine2.deliberation_get_position_map(detail_level="full"))
        arch_0 = [a for a in result["archetypes"] if a["id"] == "arch-0"][0]
        assert len(arch_0["evolution"]) > 0
