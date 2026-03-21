"""Metrics engine for OathFish MCP server.

Round metrics computation, keyword sentiment, trend analysis.
3 MCP tools: metrics_compute_round, metrics_sentiment_keyword, metrics_get_trend.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .deliberation_engine import cluster_arguments, jaccard_similarity
from .models import (
    ArgumentPosition,
    PredictionPosition,
    RoundMetrics,
    SentimentResult,
    TrendResult,
)
from .persistence import atomic_write_json, read_json
from .sentiment import compute_sentiment


class MetricsEngine:
    """Round metrics, keyword sentiment, trend analysis."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._metrics: dict[int, RoundMetrics] = {}

    def _metrics_path(self, round_n: int) -> Path:
        return self._data_dir / "deliberation" / f"metrics_round_{round_n}.json"

    def _load_deliberation_state(self) -> dict | None:
        return read_json(self._data_dir / "deliberation" / "state.json")

    def _load_round_positions(self, round_n: int) -> list:
        """Load positions for a round from deliberation state."""
        state = self._load_deliberation_state()
        if state is None:
            return []
        rounds = state.get("rounds", {})
        return rounds.get(str(round_n), rounds.get(round_n, []))

    def _parse_positions(self, raw_positions: list) -> list:
        """Parse raw position dicts into typed models."""
        parsed = []
        for pos in raw_positions:
            pos_clean = {k: v for k, v in pos.items() if k != "_type"}
            if "stance" in pos_clean and "confidence" in pos_clean and "prediction" in pos_clean:
                parsed.append(PredictionPosition.model_validate(pos_clean))
            else:
                parsed.append(ArgumentPosition.model_validate(pos_clean))
        return parsed

    async def metrics_compute_round(self, round_n: int) -> dict:
        """Aggregate metrics for a deliberation round.

        Computes diversity, engagement, stability, coalitions, cluster_count.
        Diversity index = null with INSUFFICIENT_DATA flag when total_unique_arguments < 5.
        """
        now = datetime.now(timezone.utc).isoformat()
        raw_positions = self._load_round_positions(round_n)
        positions = self._parse_positions(raw_positions)

        # Extract argument positions
        arg_positions = [p for p in positions if isinstance(p, ArgumentPosition)]

        # Engagement: avg argument count per archetype
        if arg_positions:
            engagement = sum(len(p.key_arguments) for p in arg_positions) / len(arg_positions)
        else:
            engagement = 0.0

        # All unique arguments for clustering
        all_arguments: list[str] = []
        for pos in arg_positions:
            all_arguments.extend(pos.key_arguments)

        unique_arguments = list(set(all_arguments))
        total_unique = len(unique_arguments)

        # Clustering
        clusters = cluster_arguments(unique_arguments)
        cluster_count = len(clusters)

        # Diversity index with low-N guard
        if total_unique < 5:
            diversity = None
            diversity_flag = "INSUFFICIENT_DATA"
        else:
            diversity = cluster_count / total_unique if total_unique > 0 else None
            diversity_flag = ""

        # Stability: avg Jaccard vs previous round
        stability = 0.0
        if round_n >= 2:
            prev_raw = self._load_round_positions(round_n - 1)
            prev_positions = self._parse_positions(prev_raw)
            prev_arg_map: dict[str, set[str]] = {}
            for pos in prev_positions:
                if isinstance(pos, ArgumentPosition):
                    prev_arg_map[pos.archetype_id] = set(pos.key_arguments)

            jaccard_values: list[float] = []
            for pos in arg_positions:
                prev_args = prev_arg_map.get(pos.archetype_id, set())
                curr_args = set(pos.key_arguments)
                jaccard_values.append(jaccard_similarity(curr_args, prev_args))

            stability = sum(jaccard_values) / len(jaccard_values) if jaccard_values else 0.0

        # Coalitions: groups of archetypes with pairwise argument Jaccard > 0.6
        archetype_args: dict[str, set[str]] = {}
        for pos in arg_positions:
            archetype_args[pos.archetype_id] = set(pos.key_arguments)

        arch_ids = list(archetype_args.keys())
        # Union-find for coalition detection
        parent = {aid: aid for aid in arch_ids}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for i, aid_a in enumerate(arch_ids):
            for aid_b in arch_ids[i + 1:]:
                if jaccard_similarity(archetype_args[aid_a], archetype_args[aid_b]) > 0.6:
                    union(aid_a, aid_b)

        coalition_map: dict[str, list[str]] = {}
        for aid in arch_ids:
            root = find(aid)
            coalition_map.setdefault(root, []).append(aid)

        coalitions = [members for members in coalition_map.values() if len(members) > 1]

        metrics = RoundMetrics(
            round_n=round_n,
            diversity=diversity,
            engagement=engagement,
            stability=stability,
            coalitions=coalitions,
            cluster_count=cluster_count,
            total_unique_arguments=total_unique,
            timestamp=now,
            diversity_flag=diversity_flag,
        )

        # Persist
        self._metrics[round_n] = metrics
        atomic_write_json(self._metrics_path(round_n), metrics)

        return metrics.model_dump(mode="json")

    async def metrics_sentiment_keyword(self, text: str) -> dict:
        """Deterministic keyword-based sentiment score (0.7-weight component of D-01)."""
        result = compute_sentiment(text)
        return result.model_dump(mode="json")

    async def metrics_get_trend(
        self,
        metric_name: str,
        last_n_rounds: int = 6,
    ) -> dict:
        """Return time series of a named metric across rounds.

        Supported metrics: diversity, engagement, stability, cluster_count.
        """
        values: list[dict] = []

        # Load metrics from disk for all available rounds
        for round_n in range(1, last_n_rounds + 1):
            data = read_json(self._metrics_path(round_n))
            if data is None:
                continue

            metric_value = data.get(metric_name)
            if metric_value is not None:
                values.append({"round": round_n, "value": metric_value})

        # Determine trend direction
        if len(values) < 2:
            trend = "stable"
        else:
            numeric_values = [v["value"] for v in values if isinstance(v["value"], (int, float))]
            if len(numeric_values) < 2:
                trend = "stable"
            else:
                # Simple linear trend: compare first half avg to second half avg
                mid = len(numeric_values) // 2
                first_half = sum(numeric_values[:mid]) / mid
                second_half = sum(numeric_values[mid:]) / (len(numeric_values) - mid)
                diff = second_half - first_half

                if abs(diff) < 0.05:
                    trend = "stable"
                elif diff > 0:
                    trend = "increasing"
                else:
                    trend = "decreasing"

        result = TrendResult(
            metric=metric_name,
            values=values,
            trend=trend,
        )
        return result.model_dump(mode="json")


def register_tools(app, data_dir: Path) -> None:
    """Register metrics MCP tools on the server."""
    engine = MetricsEngine(data_dir)

    @app.tool()
    async def metrics_compute_round(round_n: int) -> dict:
        """Compute aggregate metrics for a deliberation round.

        Returns diversity index, engagement, stability, coalitions, cluster count.
        Diversity is null with INSUFFICIENT_DATA flag when < 5 unique arguments.

        Args:
            round_n: Round number to compute metrics for
        """
        return await engine.metrics_compute_round(round_n)

    @app.tool()
    async def metrics_sentiment_keyword(text: str) -> dict:
        """Compute deterministic keyword-based sentiment score.

        Uses positive/negative word lists. Score range: [-1.0, 1.0].
        Same text always produces same score (C-02 deterministic).

        Args:
            text: Text to analyze for sentiment
        """
        return await engine.metrics_sentiment_keyword(text)

    @app.tool()
    async def metrics_get_trend(
        metric_name: str,
        last_n_rounds: int = 6,
    ) -> dict:
        """Get time series and trend direction for a named metric.

        Args:
            metric_name: One of: diversity, engagement, stability, cluster_count
            last_n_rounds: How many rounds to include (default 6)
        """
        return await engine.metrics_get_trend(metric_name, last_n_rounds)
