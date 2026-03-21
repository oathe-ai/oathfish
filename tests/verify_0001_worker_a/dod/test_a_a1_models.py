"""DoD A-A.1: engine/models.py -- All models construct, serialize, round-trip.

Spec claims:
- ~30 Pydantic models
- RunPhase enum: 9 values (INIT, UNDERSTAND, BASELINE_AMPLIFY, DELIBERATE, AMPLIFY, SYNTHESIZE, INTERACT, COMPLETE, ERROR)
- RoundType enum: 4 values (FREE_FORM, STRUCTURED_DEBATE, SCENARIO_REACTION, PREDICTION)
- PredictionPosition: 13 fields including coalition_alignment
- ArgumentPosition: NO stance/confidence fields (C-33)
- Position = Union[ArgumentPosition, PredictionPosition]
- Archetype.grounding_sources is list[str]
- Diversity index null when < 5 args with INSUFFICIENT_DATA flag
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from engine.models import (
    RunPhase,
    RoundType,
    ConvergenceRecommendation,
    RunConfig,
    StateHistoryEntry,
    CheckpointData,
    RunState,
    Archetype,
    ArgumentPosition,
    PredictionPosition,
    ArgumentEvolution,
    PredictionEvolution,
    RoundPlan,
    RoundSummary,
    DeliberationState,
    GraphNode,
    GraphEdge,
    GraphState,
    GraphOntology,
    EntityType,
    EdgeType,
    AmplificationResult,
    AmplificationConfig,
    ArchetypeDistribution,
    AggregateResult,
    AmplificationState,
    RoundMetrics,
    SentimentResult,
    TrendResult,
    ConvergenceResult,
    Position,
)


class TestRunPhaseEnum:
    """Spec: 9 values -- 7 pipeline phases + INIT + ERROR."""

    def test_runphase_has_exactly_9_values(self):
        values = list(RunPhase)
        assert len(values) == 9, f"Expected 9 RunPhase values, got {len(values)}: {[v.value for v in values]}"

    def test_runphase_contains_all_required_states(self):
        required = {"INIT", "UNDERSTAND", "BASELINE_AMPLIFY", "DELIBERATE", "AMPLIFY", "SYNTHESIZE", "INTERACT", "COMPLETE", "ERROR"}
        actual = {phase.value for phase in RunPhase}
        assert required == actual, f"Missing: {required - actual}, Extra: {actual - required}"

    def test_runphase_is_string_enum(self):
        assert isinstance(RunPhase.INIT.value, str)
        assert RunPhase.INIT == "INIT"


class TestRoundTypeEnum:
    """Spec: 4 values -- FREE_FORM, STRUCTURED_DEBATE, SCENARIO_REACTION, PREDICTION (NOT INDEPENDENT_PREDICTION)."""

    def test_roundtype_has_exactly_4_values(self):
        values = list(RoundType)
        assert len(values) == 4, f"Expected 4 RoundType values, got {len(values)}: {[v.value for v in values]}"

    def test_roundtype_contains_all_required_types(self):
        required = {"FREE_FORM", "STRUCTURED_DEBATE", "SCENARIO_REACTION", "PREDICTION"}
        actual = {rt.value for rt in RoundType}
        assert required == actual, f"Missing: {required - actual}, Extra: {actual - required}"

    def test_no_independent_prediction(self):
        """Spec correction: 'INDEPENDENT_PREDICTION' was renamed to 'PREDICTION'."""
        values = {rt.value for rt in RoundType}
        assert "INDEPENDENT_PREDICTION" not in values, "INDEPENDENT_PREDICTION should not exist; use PREDICTION"


class TestPredictionPosition:
    """Spec: 13 fields including coalition_alignment. This is the single source of truth (SC-07)."""

    def test_has_all_13_fields(self):
        fields = PredictionPosition.model_fields
        required_13 = [
            "archetype_id", "round_n", "prediction", "decision", "stance",
            "confidence", "timeframe", "base_rate_anchor", "key_uncertainties",
            "falsification_criteria", "second_order_effects", "cascade_susceptibility",
            "coalition_alignment",
        ]
        for field in required_13:
            assert field in fields, f"PredictionPosition missing field: {field}"
        assert len(required_13) == 13

    def test_field_count_is_13(self):
        """Spec says exactly 13 fields per feature-request.md:546-561."""
        fields = PredictionPosition.model_fields
        assert len(fields) == 13, f"Expected 13 fields, got {len(fields)}: {sorted(fields.keys())}"

    def test_stance_bounded_negative1_to_1(self):
        pos = PredictionPosition(
            archetype_id="test", round_n=6, prediction="test",
            decision="adopt", stance=0.5, confidence=0.8,
        )
        assert -1.0 <= pos.stance <= 1.0

    def test_stance_rejects_out_of_bounds(self):
        import pytest
        with pytest.raises(Exception):
            PredictionPosition(
                archetype_id="test", round_n=6, prediction="test",
                decision="adopt", stance=1.5, confidence=0.8,
            )

    def test_confidence_bounded_0_to_1(self):
        pos = PredictionPosition(
            archetype_id="test", round_n=6, prediction="test",
            decision="adopt", stance=0.5, confidence=0.8,
        )
        assert 0.0 <= pos.confidence <= 1.0

    def test_cascade_susceptibility_bounded_0_to_1(self):
        pos = PredictionPosition(
            archetype_id="test", round_n=6, prediction="test",
            decision="adopt", stance=0.0, confidence=0.5,
            cascade_susceptibility=0.7,
        )
        assert 0.0 <= pos.cascade_susceptibility <= 1.0

    def test_coalition_alignment_is_list_str(self):
        pos = PredictionPosition(
            archetype_id="test", round_n=6, prediction="test",
            decision="adopt", stance=0.0, confidence=0.5,
            coalition_alignment=["arch-1", "arch-2"],
        )
        assert isinstance(pos.coalition_alignment, list)
        assert all(isinstance(x, str) for x in pos.coalition_alignment)

    def test_construct_serialize_roundtrip(self):
        pos = PredictionPosition(
            archetype_id="test-arch", round_n=6, prediction="Will adopt",
            decision="adopt", stance=0.7, confidence=0.85,
            timeframe="6 months", base_rate_anchor="Historical: 60%",
            key_uncertainties=["regulation", "competition"],
            falsification_criteria="If market share drops below 5%",
            second_order_effects=["price war", "talent drain"],
            cascade_susceptibility=0.6,
            coalition_alignment=["arch-1", "arch-3"],
        )
        json_str = pos.model_dump_json()
        roundtripped = PredictionPosition.model_validate_json(json_str)
        assert roundtripped == pos


class TestArgumentPosition:
    """Spec: Used in rounds 1-5. NO stance/confidence fields (C-33 enforcement)."""

    def test_no_stance_field(self):
        """C-33: ArgumentPosition must NOT have stance field."""
        fields = ArgumentPosition.model_fields
        assert "stance" not in fields, "ArgumentPosition should NOT have stance (C-33)"

    def test_no_confidence_field(self):
        """C-33: ArgumentPosition must NOT have confidence field."""
        fields = ArgumentPosition.model_fields
        assert "confidence" not in fields, "ArgumentPosition should NOT have confidence (C-33)"

    def test_no_prediction_field(self):
        """C-33: ArgumentPosition must NOT have prediction field."""
        fields = ArgumentPosition.model_fields
        assert "prediction" not in fields, "ArgumentPosition should NOT have prediction (C-33)"

    def test_has_required_fields(self):
        fields = ArgumentPosition.model_fields
        for field in ["archetype_id", "round_n", "position_text", "key_arguments"]:
            assert field in fields, f"ArgumentPosition missing required field: {field}"

    def test_construct_serialize_roundtrip(self):
        pos = ArgumentPosition(
            archetype_id="test-arch", round_n=2,
            position_text="I believe regulation will slow adoption",
            key_arguments=["regulatory burden", "compliance cost"],
            concerns=["market fragmentation"],
            influenced_by=["arch-sys-thinker"],
            base_rate_anchor="Similar regulations delayed adoption by 2 years",
            key_uncertainties=["enforcement timeline"],
        )
        json_str = pos.model_dump_json()
        roundtripped = ArgumentPosition.model_validate_json(json_str)
        assert roundtripped == pos


class TestPositionUnionType:
    """Spec: Position = Union[ArgumentPosition, PredictionPosition]."""

    def test_position_type_exists(self):
        assert Position is not None

    def test_argument_position_is_valid_position(self):
        arg = ArgumentPosition(
            archetype_id="test", round_n=1,
            position_text="test", key_arguments=["arg1"],
        )
        # Should be assignable to Position type
        pos: Position = arg
        assert isinstance(pos, ArgumentPosition)

    def test_prediction_position_is_valid_position(self):
        pred = PredictionPosition(
            archetype_id="test", round_n=6,
            prediction="test", decision="adopt", stance=0.5, confidence=0.8,
        )
        pos: Position = pred
        assert isinstance(pos, PredictionPosition)


class TestArchetypeModel:
    """Spec: grounding_sources is list[str], includes Worker D proposed extensions."""

    def test_grounding_sources_is_list_str(self):
        arch = Archetype(id="test", name="Test", segment="test-seg")
        assert isinstance(arch.grounding_sources, list)

    def test_has_worker_d_extensions(self):
        """Spec: is_structural, archetype_type, stubbornness_domain, grounding_search_queries."""
        fields = Archetype.model_fields
        for field in ["is_structural", "archetype_type", "stubbornness_domain", "grounding_search_queries"]:
            assert field in fields, f"Archetype missing Worker D extension: {field}"

    def test_extensions_have_defaults(self):
        """All Worker D extensions should have defaults (non-breaking)."""
        arch = Archetype(id="test", name="Test", segment="test-seg")
        assert arch.is_structural is False
        assert arch.archetype_type == "topic"
        assert arch.stubbornness_domain == ""
        assert arch.grounding_search_queries == []

    def test_construct_serialize_roundtrip(self):
        arch = Archetype(
            id="arch-historian", name="Historian", segment="structural",
            is_structural=True, archetype_type="structural",
            stubbornness_domain="historical patterns",
            grounding_sources=["Tetlock 2005", "Meadows 2008"],
        )
        json_str = arch.model_dump_json()
        roundtripped = Archetype.model_validate_json(json_str)
        assert roundtripped == arch


class TestConvergenceResult:
    """Spec: diversity_index null when < 5 args, INSUFFICIENT_DATA flag."""

    def test_diversity_index_can_be_none(self):
        result = ConvergenceResult(
            converged=False, stability_metric=0.0,
            diversity_index=None, cluster_count=2,
            total_unique_arguments=3,
            recommendation=ConvergenceRecommendation.CONTINUE,
            diversity_flag="INSUFFICIENT_DATA",
        )
        assert result.diversity_index is None
        assert result.diversity_flag == "INSUFFICIENT_DATA"

    def test_total_unique_arguments_field_exists(self):
        fields = ConvergenceResult.model_fields
        assert "total_unique_arguments" in fields


class TestRoundMetrics:
    """Spec: diversity null when < 5, INSUFFICIENT_DATA flag."""

    def test_diversity_can_be_none(self):
        m = RoundMetrics(
            round_n=1, diversity=None, engagement=2.0,
            stability=0.0, coalitions=[], cluster_count=2,
            total_unique_arguments=3, timestamp="2026-01-01T00:00:00",
            diversity_flag="INSUFFICIENT_DATA",
        )
        assert m.diversity is None

    def test_diversity_flag_field_exists(self):
        fields = RoundMetrics.model_fields
        assert "diversity_flag" in fields


class TestModelDumpJsonMode:
    """Verify .model_dump(mode='json') works for all key models (enum serialization fix)."""

    def test_runstate_model_dump_json_mode(self):
        state = RunState(
            run_id="test", state=RunPhase.INIT,
            config=RunConfig(topic="test"),
            created_at="2026-01-01T00:00:00", run_dir="/tmp/test",
        )
        dumped = state.model_dump(mode="json")
        assert dumped["state"] == "INIT"  # Must be string, not enum
        assert isinstance(json.dumps(dumped), str)  # Must be JSON-serializable

    def test_roundsummary_model_dump_json_mode(self):
        summary = RoundSummary(
            round_n=1, round_type=RoundType.FREE_FORM,
            positions=[],
        )
        dumped = summary.model_dump(mode="json")
        assert dumped["round_type"] == "FREE_FORM"

    def test_convergence_result_model_dump_json_mode(self):
        result = ConvergenceResult(
            converged=False, stability_metric=0.5,
            diversity_index=0.3, cluster_count=5,
            total_unique_arguments=10,
            recommendation=ConvergenceRecommendation.CONTINUE,
        )
        dumped = result.model_dump(mode="json")
        assert dumped["recommendation"] == "CONTINUE"
        assert isinstance(json.dumps(dumped), str)
