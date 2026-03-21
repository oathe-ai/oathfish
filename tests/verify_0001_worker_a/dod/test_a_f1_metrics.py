"""DoD A-F.1: engine/metrics_engine.py -- Deterministic computation.

Spec claims:
- metrics_compute_round, metrics_sentiment_keyword, metrics_get_trend
- Deterministic: same text = same sentiment score (C-02)
- Diversity index = null with INSUFFICIENT_DATA when < 5 arguments
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from engine.metrics_engine import MetricsEngine
from engine.deliberation_engine import DeliberationEngine


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


SAMPLE_ARCHETYPES = [
    {"id": f"arch-{i}", "name": f"Archetype {i}", "segment": f"seg-{i}"}
    for i in range(5)
]

STANDARD_ROUND_PLAN = [
    {"round_n": 1, "round_type": "FREE_FORM"},
    {"round_n": 2, "round_type": "FREE_FORM"},
    {"round_n": 3, "round_type": "PREDICTION"},
]


class TestMetricsComputeRound:
    def test_computes_metrics(self, tmp_path):
        # Set up deliberation state first
        delib = DeliberationEngine(tmp_path)
        run_async(delib.deliberation_init(SAMPLE_ARCHETYPES, 3, STANDARD_ROUND_PLAN))
        run_async(delib.deliberation_record_round(1, [
            {"archetype_id": f"arch-{i}", "position_text": f"Position {i}", "key_arguments": [f"arg-{i}-a", f"arg-{i}-b", f"arg-{i}-c"]}
            for i in range(5)
        ]))

        metrics = MetricsEngine(tmp_path)
        result = run_async(metrics.metrics_compute_round(1))
        assert "diversity" in result
        assert "engagement" in result
        assert "stability" in result
        assert "coalitions" in result
        assert "cluster_count" in result

    def test_diversity_null_under_5_unique(self, tmp_path):
        """A-H06: diversity index null when < 5 arguments."""
        delib = DeliberationEngine(tmp_path)
        run_async(delib.deliberation_init(SAMPLE_ARCHETYPES, 3, STANDARD_ROUND_PLAN))
        run_async(delib.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "test", "key_arguments": ["arg-a", "arg-b"]},
        ]))

        metrics = MetricsEngine(tmp_path)
        result = run_async(metrics.metrics_compute_round(1))
        assert result["diversity"] is None
        assert result["diversity_flag"] == "INSUFFICIENT_DATA"

    def test_persists_metrics(self, tmp_path):
        delib = DeliberationEngine(tmp_path)
        run_async(delib.deliberation_init(SAMPLE_ARCHETYPES, 3, STANDARD_ROUND_PLAN))
        run_async(delib.deliberation_record_round(1, [
            {"archetype_id": "arch-0", "position_text": "test", "key_arguments": ["arg1", "arg2", "arg3", "arg4", "arg5"]},
        ]))

        metrics = MetricsEngine(tmp_path)
        run_async(metrics.metrics_compute_round(1))
        metrics_path = tmp_path / "deliberation" / "metrics_round_1.json"
        assert metrics_path.exists()


class TestMetricsSentiment:
    def test_deterministic(self, tmp_path):
        """C-02: same text = same score."""
        metrics = MetricsEngine(tmp_path)
        text = "This is a great and wonderful opportunity for growth"
        r1 = run_async(metrics.metrics_sentiment_keyword(text))
        r2 = run_async(metrics.metrics_sentiment_keyword(text))
        assert r1["score"] == r2["score"]
        assert r1["label"] == r2["label"]
        assert r1["confidence"] == r2["confidence"]

    def test_positive_text(self, tmp_path):
        metrics = MetricsEngine(tmp_path)
        result = run_async(metrics.metrics_sentiment_keyword("excellent wonderful great amazing"))
        assert result["score"] > 0
        assert result["label"] == "positive"

    def test_negative_text(self, tmp_path):
        metrics = MetricsEngine(tmp_path)
        result = run_async(metrics.metrics_sentiment_keyword("terrible horrible awful disaster"))
        assert result["score"] < 0
        assert result["label"] == "negative"


class TestMetricsTrend:
    def test_trend_analysis(self, tmp_path):
        metrics = MetricsEngine(tmp_path)
        result = run_async(metrics.metrics_get_trend("diversity"))
        assert "metric" in result
        assert "values" in result
        assert "trend" in result
        assert result["metric"] == "diversity"
