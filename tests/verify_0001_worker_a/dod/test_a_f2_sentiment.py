"""DoD A-F.2: engine/sentiment.py -- Pure function, no randomness, no LLM, no network I/O.

Spec claims:
- ~200 positive words, ~200 negative words
- compute_sentiment() is pure: same text = same score always
- Score range: [-1.0, 1.0]
- Deterministic (C-02)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from engine.sentiment import compute_sentiment, POSITIVE_WORDS, NEGATIVE_WORDS


class TestWordLists:
    """Spec: ~200 positive + ~200 negative words."""

    def test_positive_words_substantial(self):
        count = len(POSITIVE_WORDS)
        assert count >= 150, f"Expected >= 150 positive words, got {count}"

    def test_negative_words_substantial(self):
        count = len(NEGATIVE_WORDS)
        assert count >= 150, f"Expected >= 150 negative words, got {count}"

    def test_word_lists_are_frozensets(self):
        """Immutable word lists prevent accidental mutation."""
        assert isinstance(POSITIVE_WORDS, frozenset)
        assert isinstance(NEGATIVE_WORDS, frozenset)

    def test_no_overlap_between_lists(self):
        overlap = POSITIVE_WORDS & NEGATIVE_WORDS
        assert len(overlap) == 0, f"Words in both lists: {overlap}"


class TestComputeSentiment:
    """Spec: Pure function, deterministic."""

    def test_returns_sentiment_result(self):
        result = compute_sentiment("This is great")
        assert hasattr(result, 'score')
        assert hasattr(result, 'label')
        assert hasattr(result, 'confidence')

    def test_score_range(self):
        """Spec: score range [-1.0, 1.0]."""
        texts = [
            "excellent wonderful great amazing",
            "terrible horrible awful disaster",
            "the cat sat on the mat",
            "",
        ]
        for text in texts:
            result = compute_sentiment(text)
            assert -1.0 <= result.score <= 1.0, f"Score {result.score} out of range for '{text}'"

    def test_deterministic(self):
        """C-02: same text = same score always."""
        text = "The regulation will have both positive and negative effects on innovation"
        results = [compute_sentiment(text) for _ in range(10)]
        scores = [r.score for r in results]
        assert len(set(scores)) == 1, f"Non-deterministic: got different scores {set(scores)}"

    def test_positive_text_positive_score(self):
        result = compute_sentiment("excellent wonderful great amazing success")
        assert result.score > 0
        assert result.label == "positive"

    def test_negative_text_negative_score(self):
        result = compute_sentiment("terrible horrible awful disaster failure")
        assert result.score < 0
        assert result.label == "negative"

    def test_neutral_text(self):
        result = compute_sentiment("the cat sat on the mat near the door")
        assert result.label == "neutral"

    def test_empty_text(self):
        result = compute_sentiment("")
        assert result.score == 0.0
        assert result.label == "neutral"
        assert result.confidence == 0.0

    def test_no_randomness(self):
        """Run 100 times, all results must be identical."""
        text = "Mixed feelings about the terrible but innovative approach"
        first = compute_sentiment(text)
        for _ in range(99):
            result = compute_sentiment(text)
            assert result.score == first.score
            assert result.label == first.label
            assert result.confidence == first.confidence

    def test_no_imports_of_random_or_network(self):
        """Verify the module does not import random, requests, httpx, urllib, etc."""
        import importlib
        import inspect
        mod = importlib.import_module("engine.sentiment")
        source = inspect.getsource(mod)
        forbidden = ["import random", "import requests", "import httpx", "import urllib"]
        for fb in forbidden:
            assert fb not in source, f"sentiment.py should not contain '{fb}'"
