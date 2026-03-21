"""Deterministic keyword-based sentiment scoring for OathFish.

Pure function: same text always produces same score. No randomness, no LLM, no network I/O.
This is the 0.7-weight component of D-01 sentiment.
"""

from __future__ import annotations

from .models import SentimentResult

POSITIVE_WORDS: frozenset[str] = frozenset({
    "achieve", "accomplished", "achievement", "advantage", "agree", "amazing",
    "appreciate", "approval", "approved", "attractive", "beautiful", "benefit",
    "best", "better", "boost", "breakthrough", "bright", "brilliant",
    "capable", "celebrate", "certain", "champion", "clear", "comfortable",
    "commit", "compelling", "confident", "constructive", "courage",
    "creative", "decisive", "delight", "dependable", "dynamic", "eager",
    "effective", "efficient", "empower", "encourage", "endorse", "energize",
    "enhance", "enjoy", "enormous", "enthusiastic", "excellent", "exceptional",
    "excited", "exciting", "exemplary", "extraordinary", "fabulous", "fair",
    "fantastic", "favorable", "flourish", "fortunate", "freedom", "friendly",
    "fulfill", "gain", "generous", "genius", "genuine", "glad", "good",
    "graceful", "grand", "grateful", "great", "grow", "growth", "guarantee",
    "happy", "harmony", "healthy", "helpful", "hope", "hopeful", "ideal",
    "imaginative", "impressive", "improve", "improvement", "incredible",
    "independent", "influence", "ingenious", "innovation", "innovative",
    "inspire", "inspired", "integrity", "intelligent", "interesting",
    "invest", "inviting", "joy", "joyful", "kind", "knowledge", "launch",
    "lead", "leadership", "learn", "liberate", "lively", "love", "loyal",
    "lucrative", "magnificent", "master", "merit", "miracle", "modern",
    "momentum", "motivate", "natural", "noble", "nurture", "open",
    "opportunity", "optimal", "optimism", "optimistic", "organize",
    "original", "outperform", "outstanding", "overcome", "paradise",
    "passionate", "peace", "perfect", "phenomenal", "pioneer", "pleasant",
    "pleasure", "plentiful", "positive", "powerful", "practical", "praise",
    "premium", "prestige", "pride", "privilege", "proactive", "productive",
    "proficient", "profit", "profitable", "progress", "prominent", "promise",
    "promote", "proper", "prosper", "prosperity", "protect", "proud",
    "purpose", "quality", "quick", "ready", "reasonable", "recommend",
    "reform", "refresh", "reliable", "remarkable", "renew", "reputation",
    "resilient", "resolve", "respect", "restore", "reward", "rich",
    "robust", "safe", "satisfy", "secure", "significant", "simple",
    "sincere", "skill", "smart", "smooth", "solution", "spectacular",
    "stable", "stellar", "strength", "strong", "succeed", "success",
    "successful", "sufficient", "super", "superior", "support", "supreme",
    "sure", "surprise", "sustain", "terrific", "thrive", "top", "transform",
    "tremendous", "triumph", "trust", "trustworthy", "unique", "unity",
    "upbeat", "upgrade", "uplift", "valuable", "value", "versatile",
    "vibrant", "victory", "vigor", "vision", "vital", "vivid", "wealth",
    "welcome", "win", "wisdom", "wonderful", "worthy",
})

NEGATIVE_WORDS: frozenset[str] = frozenset({
    "abandon", "abuse", "accident", "accuse", "ache", "adverse", "afraid",
    "aggravate", "aggressive", "agony", "alarm", "anger", "angry", "anguish",
    "annoy", "antagonize", "anxiety", "anxious", "appalling", "argue",
    "arrogant", "assault", "attack", "awful", "bad", "bankrupt", "barrier",
    "betray", "bias", "bitter", "blame", "bleak", "blind", "block",
    "boring", "bother", "break", "brutal", "burden", "burn", "calamity",
    "cancel", "catastrophe", "chaos", "cheap", "cheat", "clash", "close",
    "collapse", "complain", "complication", "concern", "condemn", "confuse",
    "conspiracy", "constraint", "contaminate", "contempt", "contradict",
    "controversial", "corrupt", "costly", "crash", "crazy", "crisis",
    "critical", "cruel", "crush", "crying", "damage", "danger", "dangerous",
    "dark", "dead", "deadly", "debt", "decay", "deceive", "decline",
    "defect", "deficit", "delay", "demolish", "deny", "deplete", "depress",
    "deprive", "destroy", "destruction", "detain", "deteriorate",
    "devastating", "difficult", "diminish", "dire", "dirty", "disable",
    "disadvantage", "disagree", "disappear", "disappoint", "disaster",
    "disbelief", "discrimination", "disease", "disgrace", "disgusting",
    "dislike", "dismiss", "disorder", "dispute", "disrupt", "distort",
    "distress", "disturb", "doubt", "downfall", "downturn", "dreadful",
    "drop", "dull", "dump", "empty", "endanger", "enemy", "erode", "error",
    "evil", "exaggerate", "exclude", "exhaust", "exploit", "expose",
    "extreme", "fail", "failure", "fake", "fatal", "fault", "fear",
    "fierce", "fight", "flaw", "flee", "flood", "fool", "force",
    "foreclose", "forget", "fraud", "freeze", "frustrate", "fury",
    "gloomy", "grave", "greed", "grief", "grim", "gross", "guilt", "harm",
    "harsh", "hate", "hatred", "hazard", "helpless", "hesitate", "hinder",
    "horrible", "horrify", "hostile", "humiliate", "hurt", "ignore",
    "illegal", "immoral", "impair", "impose", "impossible", "inadequate",
    "incompetent", "incorrect", "ineffective", "inferior", "inflame",
    "injure", "injustice", "insecure", "insult", "interfere", "intimidate",
    "invade", "irritate", "isolate", "jeopardize", "kill", "lack", "lag",
    "lame", "lawsuit", "lazy", "leak", "lie", "limit", "litigation",
    "loneliness", "lose", "loss", "lost", "lousy", "manipulate", "menace",
    "mess", "miserable", "mislead", "mistake", "mock", "monopoly", "mourn",
    "nasty", "negative", "neglect", "nightmare", "obstacle", "offend",
    "oppress", "outrage", "overload", "overwhelm", "pain", "panic",
    "penalty", "peril", "pessimistic", "plague", "plunge", "poison",
    "pollute", "poor", "poverty", "pressure", "problem", "prohibit",
    "protest", "provoke", "punish", "rage", "reckless", "recession",
    "regret", "reject", "reluctant", "resent", "resign", "restrict",
    "retaliate", "revenge", "revolt", "ridicule", "rigid", "risk", "rob",
    "ruin", "sabotage", "sacrifice", "sad", "scam", "scandal", "scare",
    "scold", "severe", "shame", "shock", "shortage", "shrink", "sick",
    "sinister", "slander", "slump", "smear", "smother", "snub",
    "stagnate", "steal", "strain", "stress", "strike", "struggle",
    "stubborn", "stupid", "suffer", "suppress", "suspect", "suspicious",
    "terrible", "terror", "threat", "threaten", "tragic", "trauma",
    "trouble", "ugly", "uncertain", "undermine", "unfair", "unfortunate",
    "unhappy", "unstable", "upset", "urgent", "useless", "vandalize",
    "vicious", "victim", "violate", "violence", "volatile", "vulnerable",
    "war", "warn", "warning", "waste", "weak", "weaken", "wicked",
    "withdraw", "worse", "worsen", "worst", "worthless", "wreck", "wrong",
})


def compute_sentiment(text: str) -> SentimentResult:
    """Compute deterministic keyword-based sentiment score.

    Score = (positive_count - negative_count) / total_scored_count.
    Range: [-1.0, 1.0]. Confidence based on proportion of scored words.
    """
    words = []
    for word in text.lower().split():
        cleaned = "".join(c for c in word if c.isalnum())
        if cleaned:
            words.append(cleaned)

    if not words:
        return SentimentResult(score=0.0, label="neutral", confidence=0.0)

    positive_count = sum(1 for w in words if w in POSITIVE_WORDS)
    negative_count = sum(1 for w in words if w in NEGATIVE_WORDS)
    scored_count = positive_count + negative_count

    if scored_count == 0:
        return SentimentResult(score=0.0, label="neutral", confidence=0.0)

    score = (positive_count - negative_count) / scored_count
    # Clamp to [-1.0, 1.0] (should already be, but defensive)
    score = max(-1.0, min(1.0, score))

    # Confidence: proportion of words that matched a sentiment word
    confidence = min(1.0, scored_count / len(words))

    if score > 0.05:
        label = "positive"
    elif score < -0.05:
        label = "negative"
    else:
        label = "neutral"

    return SentimentResult(score=score, label=label, confidence=confidence)
