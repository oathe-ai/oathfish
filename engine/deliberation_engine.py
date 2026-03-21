"""Deliberation engine for OathFish MCP server.

Round management, polymorphic position tracking (SPEC-01), Jaccard-based evolution (AMB-01),
diversity-preserving convergence detection (C-32).

5 MCP tools: deliberation_init, deliberation_record_round, deliberation_track_evolution,
deliberation_check_convergence, deliberation_get_position_map.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

from .models import (
    Archetype,
    ArgumentEvolution,
    ArgumentPosition,
    ConvergenceRecommendation,
    ConvergenceResult,
    DeliberationState,
    PredictionEvolution,
    PredictionPosition,
    Position,
    RoundPlan,
    RoundType,
)
from .persistence import atomic_write_json, read_json


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "this", "that", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "could", "should", "may", "might", "shall",
    "can", "not", "no", "so", "if", "as", "its", "they", "them", "their",
    "we", "our", "you", "your", "he", "she", "his", "her", "i", "me", "my",
    "all", "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "than", "too", "very", "just", "about", "above", "after",
    "again", "also", "any", "because", "before", "between", "into", "over",
    "under", "up", "down", "out", "then", "there", "here", "when", "where",
    "how", "what", "which", "who", "whom", "why",
})


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase word set, filtering stop words."""
    words = set()
    for word in text.lower().split():
        cleaned = "".join(c for c in word if c.isalnum())
        if cleaned and cleaned not in STOP_WORDS and len(cleaned) > 1:
            words.add(cleaned)
    return words


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def cluster_arguments(all_arguments: list[str], threshold: float = 0.5) -> list[set[str]]:
    """Single-linkage clustering based on word-level Jaccard.

    Tokenizes each argument into word sets. If Jaccard > threshold, link them.
    Find connected components via union-find.
    """
    if not all_arguments:
        return []

    tokenized = [_tokenize(arg) for arg in all_arguments]
    n = len(all_arguments)

    # Union-find
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    # Build adjacency
    for i in range(n):
        for j in range(i + 1, n):
            if jaccard_similarity(tokenized[i], tokenized[j]) > threshold:
                union(i, j)

    # Collect clusters
    clusters_map: dict[int, set[str]] = {}
    for i in range(n):
        root = find(i)
        if root not in clusters_map:
            clusters_map[root] = set()
        clusters_map[root].add(all_arguments[i])

    return list(clusters_map.values())


# ---------------------------------------------------------------------------
# Deliberation Engine
# ---------------------------------------------------------------------------

class DeliberationEngine:
    """Round management, polymorphic position tracking, evolution, convergence."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._state: DeliberationState | None = None

    def _state_path(self) -> Path:
        return self._data_dir / "deliberation" / "state.json"

    def _persist(self) -> None:
        assert self._state is not None
        # Serialize with type discrimination for positions
        data = self._state.model_dump(mode="json")
        # Add type tags for polymorphic round deserialization
        for round_n_str, positions in data.get("rounds", {}).items():
            for pos in positions:
                if "stance" in pos and "confidence" in pos and "prediction" in pos:
                    pos["_type"] = "prediction"
                else:
                    pos["_type"] = "argument"
        for round_n_str, evolutions in data.get("evolutions", {}).items():
            for evo in evolutions:
                if "jaccard_similarity" in evo:
                    evo["_type"] = "argument"
                else:
                    evo["_type"] = "prediction"
        atomic_write_json(self._state_path(), data)

    def _load(self) -> DeliberationState | None:
        data = read_json(self._state_path())
        if data is None:
            return None
        # Reconstruct polymorphic positions from type tags
        rounds: dict[int, list[Position]] = {}
        for round_n_str, positions in data.get("rounds", {}).items():
            round_n = int(round_n_str)
            round_positions: list[Position] = []
            for pos in positions:
                pos.pop("_type", None)
                if "stance" in pos and "confidence" in pos and "prediction" in pos:
                    round_positions.append(PredictionPosition.model_validate(pos))
                else:
                    round_positions.append(ArgumentPosition.model_validate(pos))
            rounds[round_n] = round_positions
        data["rounds"] = rounds

        evolutions: dict[int, list] = {}
        for round_n_str, evos in data.get("evolutions", {}).items():
            round_n = int(round_n_str)
            evo_list = []
            for evo in evos:
                evo.pop("_type", None)
                if "jaccard_similarity" in evo:
                    evo_list.append(ArgumentEvolution.model_validate(evo))
                else:
                    evo_list.append(PredictionEvolution.model_validate(evo))
            evolutions[round_n] = evo_list
        data["evolutions"] = evolutions

        return DeliberationState.model_validate(data)

    def _ensure_loaded(self) -> DeliberationState:
        if self._state is None:
            self._state = self._load()
        if self._state is None:
            raise ValueError("No active deliberation. Call deliberation_init first.")
        return self._state

    def _get_round_type(self, round_n: int) -> RoundType:
        """Get the round type from the round plan."""
        state = self._ensure_loaded()
        for plan in state.round_plan:
            if plan.round_n == round_n:
                return plan.round_type
        raise ValueError(f"Round {round_n} not in round plan")

    async def deliberation_init(
        self,
        archetypes: list[dict],
        round_count: int,
        round_types: list[dict],
    ) -> dict:
        """Initialize deliberation state with archetype registry and round plan."""
        parsed_archetypes = [Archetype.model_validate(a) for a in archetypes]
        parsed_plan = [RoundPlan.model_validate(rt) for rt in round_types]
        delib_id = f"delib-{uuid.uuid4().hex[:8]}"

        self._state = DeliberationState(
            deliberation_id=delib_id,
            archetypes=parsed_archetypes,
            round_count=round_count,
            round_plan=parsed_plan,
        )
        self._persist()

        return {
            "deliberation_id": delib_id,
            "archetype_count": len(parsed_archetypes),
            "round_plan": [rp.model_dump(mode="json") for rp in parsed_plan],
        }

    async def deliberation_record_round(
        self,
        round_n: int,
        positions: list[dict],
    ) -> dict:
        """Save each archetype's position for round N.

        Polymorphic (SPEC-01): validates as ArgumentPosition or PredictionPosition
        based on the round_plan, not hardcoded round number.
        """
        state = self._ensure_loaded()
        round_type = self._get_round_type(round_n)
        now = datetime.now(timezone.utc).isoformat()

        parsed_positions: list[Position] = []
        is_prediction = round_type == RoundType.PREDICTION

        for pos_dict in positions:
            pos_dict["round_n"] = round_n
            if is_prediction:
                # Validate as PredictionPosition -- reject ArgumentPosition fields
                parsed_positions.append(PredictionPosition.model_validate(pos_dict))
            else:
                # Validate as ArgumentPosition -- reject if numeric fields present
                if "stance" in pos_dict or "confidence" in pos_dict:
                    raise ValueError(
                        f"Round {round_n} is type {round_type.value}, not PREDICTION. "
                        f"Cannot include stance/confidence fields (C-33)."
                    )
                parsed_positions.append(ArgumentPosition.model_validate(pos_dict))

        state.rounds[round_n] = parsed_positions
        state.current_round = round_n
        self._persist()

        return {
            "round_n": round_n,
            "positions_recorded": len(parsed_positions),
            "round_type": "prediction" if is_prediction else "argument",
            "timestamp": now,
        }

    async def deliberation_track_evolution(self, round_n: int) -> dict:
        """Compute argument evolution between round N and N-1.

        Rounds 1-5: Jaccard similarity on key_arguments.
        Round 6 (prediction): absolute stance/confidence values.
        """
        state = self._ensure_loaded()
        round_type = self._get_round_type(round_n)

        evolutions: list[Union[ArgumentEvolution, PredictionEvolution]] = []

        if round_type == RoundType.PREDICTION:
            # Prediction evolution: absolute values
            current_positions = state.rounds.get(round_n, [])
            archetype_map = {a.id: a for a in state.archetypes}

            for pos in current_positions:
                if not isinstance(pos, PredictionPosition):
                    continue
                archetype = archetype_map.get(pos.archetype_id)
                # stance_vs_initial: we store 0.0 since initial_stance is qualitative text
                evolutions.append(PredictionEvolution(
                    archetype_id=pos.archetype_id,
                    round_n=round_n,
                    stance=pos.stance,
                    confidence=pos.confidence,
                    stance_vs_initial=0.0,  # Qualitative comparison done by coordinator
                ))
        else:
            # Argument evolution: Jaccard similarity
            if round_n < 2:
                return {
                    "round_n": round_n,
                    "evolutions": [],
                    "note": "No previous round to compare (round 1)",
                }

            current_positions = state.rounds.get(round_n, [])
            prev_positions = state.rounds.get(round_n - 1, [])

            # Build lookup: archetype_id -> position
            prev_map: dict[str, ArgumentPosition] = {}
            for pos in prev_positions:
                if isinstance(pos, ArgumentPosition):
                    prev_map[pos.archetype_id] = pos

            for pos in current_positions:
                if not isinstance(pos, ArgumentPosition):
                    continue
                prev = prev_map.get(pos.archetype_id)
                if prev is None:
                    evolutions.append(ArgumentEvolution(
                        archetype_id=pos.archetype_id,
                        round_n=round_n,
                        jaccard_similarity=0.0,
                        new_arguments=list(pos.key_arguments),
                        dropped_arguments=[],
                        influence_chain=list(pos.influenced_by),
                    ))
                    continue

                curr_args = set(pos.key_arguments)
                prev_args = set(prev.key_arguments)

                evolutions.append(ArgumentEvolution(
                    archetype_id=pos.archetype_id,
                    round_n=round_n,
                    jaccard_similarity=jaccard_similarity(curr_args, prev_args),
                    new_arguments=list(curr_args - prev_args),
                    dropped_arguments=list(prev_args - curr_args),
                    influence_chain=list(pos.influenced_by),
                    shift_summary=(
                        f"Anchor changed from '{prev.base_rate_anchor}' to '{pos.base_rate_anchor}'"
                        if prev.base_rate_anchor != pos.base_rate_anchor
                        else ""
                    ),
                ))

        state.evolutions[round_n] = evolutions
        self._persist()

        return {
            "round_n": round_n,
            "evolutions": [e.model_dump(mode="json") for e in evolutions],
        }

    async def deliberation_check_convergence(self, window_size: int = 3) -> dict:
        """Check if arguments are stabilizing. Returns diversity index and recommendation.

        Diversity index = distinct_clusters / total_unique_arguments.
        INSUFFICIENT_DATA guard: null when total_unique_arguments < 5.
        INJECT_CONTRARIAN: when cluster_count < 3 before round 5, or diversity < 0.15 before round 5.
        """
        state = self._ensure_loaded()

        # Gather all argument positions from recent rounds
        current_round = state.current_round
        round_type = self._get_round_type(current_round)

        if round_type == RoundType.PREDICTION:
            # Prediction-based convergence: std dev of stances
            positions = state.rounds.get(current_round, [])
            stances = [
                p.stance for p in positions if isinstance(p, PredictionPosition)
            ]
            if not stances:
                return ConvergenceResult(
                    converged=False,
                    stability_metric=0.0,
                    diversity_index=None,
                    cluster_count=0,
                    total_unique_arguments=0,
                    recommendation=ConvergenceRecommendation.CONTINUE,
                    diversity_flag="INSUFFICIENT_DATA",
                ).model_dump(mode="json")

            mean_stance = sum(stances) / len(stances)
            variance = sum((s - mean_stance) ** 2 for s in stances) / len(stances)
            std_dev = variance ** 0.5
            converged = std_dev < 0.1
            warning = converged and current_round < state.round_count

            return ConvergenceResult(
                converged=converged,
                stability_metric=1.0 - std_dev,
                diversity_index=std_dev,  # Use std_dev as diversity proxy for predictions
                cluster_count=len(stances),
                total_unique_arguments=len(stances),
                recommendation=(
                    ConvergenceRecommendation.INJECT_CONTRARIAN if warning
                    else ConvergenceRecommendation.CONVERGE if converged
                    else ConvergenceRecommendation.CONTINUE
                ),
            ).model_dump(mode="json")

        # Argument-based convergence (rounds 1-5)
        # Collect all unique arguments from current round
        all_arguments: list[str] = []
        for pos in state.rounds.get(current_round, []):
            if isinstance(pos, ArgumentPosition):
                all_arguments.extend(pos.key_arguments)

        total_unique = len(set(all_arguments))
        clusters = cluster_arguments(list(set(all_arguments)))
        cluster_count = len(clusters)

        # Diversity index with low-N guard (SK-11)
        if total_unique < 5:
            diversity_index = None
            diversity_flag = "INSUFFICIENT_DATA"
        else:
            diversity_index = cluster_count / total_unique if total_unique > 0 else None
            diversity_flag = ""

        # Stability: avg Jaccard across window
        stability_values: list[float] = []
        for r in range(max(2, current_round - window_size + 1), current_round + 1):
            evos = state.evolutions.get(r, [])
            for evo in evos:
                if isinstance(evo, ArgumentEvolution):
                    stability_values.append(evo.jaccard_similarity)

        stability = (
            sum(stability_values) / len(stability_values)
            if stability_values
            else 0.0
        )

        converged = stability > 0.8 and len(stability_values) >= window_size

        # INJECT_CONTRARIAN conditions (C-32):
        # - cluster_count < 3 before round 5
        # - diversity_index < 0.15 before round 5 (when sufficient data)
        premature_consensus = False
        if current_round < 5:
            if cluster_count < 3:
                premature_consensus = True
            elif diversity_index is not None and diversity_index < 0.15:
                premature_consensus = True

        if premature_consensus:
            recommendation = ConvergenceRecommendation.INJECT_CONTRARIAN
        elif converged:
            recommendation = ConvergenceRecommendation.CONVERGE
        else:
            recommendation = ConvergenceRecommendation.CONTINUE

        return ConvergenceResult(
            converged=converged,
            stability_metric=stability,
            diversity_index=diversity_index,
            cluster_count=cluster_count,
            total_unique_arguments=total_unique,
            recommendation=recommendation,
            diversity_flag=diversity_flag,
        ).model_dump(mode="json")

    async def deliberation_get_position_map(
        self,
        detail_level: str = "summary",
        archetype_ids: list[str] | None = None,
    ) -> dict:
        """Return position map with pagination support.

        detail_level="summary": latest position per archetype (compact).
        detail_level="full": full evolution history across all rounds.
        archetype_ids: filter to specific archetypes.
        """
        state = self._ensure_loaded()

        # Filter archetypes
        archetypes = state.archetypes
        if archetype_ids:
            archetypes = [a for a in archetypes if a.id in archetype_ids]

        result_archetypes = []
        for archetype in archetypes:
            entry: dict = {
                "id": archetype.id,
                "name": archetype.name,
                "segment": archetype.segment,
            }

            # Find latest position
            current_pos = None
            for round_n in sorted(state.rounds.keys(), reverse=True):
                for pos in state.rounds[round_n]:
                    if pos.archetype_id == archetype.id:
                        current_pos = pos.model_dump(mode="json")
                        break
                if current_pos is not None:
                    break

            entry["current_position"] = current_pos

            if detail_level == "full":
                # Include full evolution history
                evolution_history = []
                for round_n in sorted(state.rounds.keys()):
                    for pos in state.rounds[round_n]:
                        if pos.archetype_id == archetype.id:
                            evolution_history.append({
                                "round_n": round_n,
                                "position": pos.model_dump(mode="json"),
                            })

                    evos = state.evolutions.get(round_n, [])
                    for evo in evos:
                        if evo.archetype_id == archetype.id:
                            evolution_history.append({
                                "round_n": round_n,
                                "evolution": evo.model_dump(mode="json"),
                            })

                entry["evolution"] = evolution_history
            else:
                entry["evolution"] = []

            result_archetypes.append(entry)

        return {"archetypes": result_archetypes}


def register_tools(app, data_dir: Path) -> None:
    """Register deliberation MCP tools on the server."""
    engine = DeliberationEngine(data_dir)

    @app.tool()
    async def deliberation_init(
        archetypes: list[dict],
        round_count: int,
        round_types: list[dict],
    ) -> dict:
        """Initialize deliberation with archetype registry and round plan.

        Args:
            archetypes: List of Archetype dicts (from understand phase)
            round_count: Total rounds (default 6)
            round_types: List of {round_n, round_type} mappings (e.g., round 6 = PREDICTION)
        """
        return await engine.deliberation_init(archetypes, round_count, round_types)

    @app.tool()
    async def deliberation_record_round(
        round_n: int,
        positions: list[dict],
    ) -> dict:
        """Record archetype positions for a deliberation round.

        Polymorphic: validates as ArgumentPosition (rounds 1-5) or PredictionPosition
        (final round) based on the round plan set in deliberation_init.

        Args:
            round_n: Round number (1-indexed)
            positions: List of position dicts (fields depend on round type)
        """
        return await engine.deliberation_record_round(round_n, positions)

    @app.tool()
    async def deliberation_track_evolution(round_n: int) -> dict:
        """Compute argument evolution between round N and N-1.

        Rounds 1-5: Jaccard similarity on key_arguments sets.
        Final round (prediction): absolute stance/confidence values.

        Args:
            round_n: Round to compute evolution for (>= 2 for argument rounds)
        """
        return await engine.deliberation_track_evolution(round_n)

    @app.tool()
    async def deliberation_check_convergence(window_size: int = 3) -> dict:
        """Check if archetype arguments are stabilizing. Returns diversity index.

        Returns converged status, stability metric, diversity index (null if < 5 args),
        cluster count, and recommendation (CONTINUE/CONVERGE/INJECT_CONTRARIAN).

        Args:
            window_size: Number of consecutive rounds to check (default 3)
        """
        return await engine.deliberation_check_convergence(window_size)

    @app.tool()
    async def deliberation_get_position_map(
        detail_level: str = "summary",
        archetype_ids: list[str] | None = None,
    ) -> dict:
        """Get position map across archetypes with pagination.

        Args:
            detail_level: "summary" (latest position) or "full" (all rounds + evolution)
            archetype_ids: Filter to specific archetype IDs (None = all)
        """
        return await engine.deliberation_get_position_map(detail_level, archetype_ids)
