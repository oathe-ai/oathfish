"""
engine/amplification_sdk.py

Python SDK amplification engine. Replaces amplify.sh.
Handles both BASELINE_AMPLIFY (stateless) and AMPLIFY (post-deliberation with digest) modes.

IMPORTANT: Amplification calls are TOOL-FREE (allowed_tools=[]) and SINGLE-TURN
(max_turns=1) per headless-analysis.md:120, 229-233. This prevents wasted tokens
on tool-use reasoning at 1500 calls.

IMPORTANT: INFORMED mode uses deliberation DIGEST (500-1000 tokens) injected into
system_prompt, NOT --resume. --resume with full deliberation context (100K-500K tokens)
at 1500 calls would cost 50-100x more than stateless baseline (headless-analysis.md:275-281).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from pydantic import BaseModel

from claude_agent_sdk import ClaudeAgentOptions, query, ResultMessage, ProcessError

from .models import PredictionPosition, Archetype

logger = logging.getLogger("oathfish.amplification")


class AmplificationMode(str, Enum):
    BASELINE = "baseline"       # Stateless, no session context (C-26)
    INFORMED = "informed"       # Deliberation DIGEST injected into system_prompt (C-21)


@dataclass
class SDKAmplificationConfig:
    """Configuration for a single amplification batch.

    NOTE: Named SDKAmplificationConfig to avoid collision with
    engine.models.AmplificationConfig (Worker A's MCP-facing model).
    """
    archetypes: list[Archetype]
    scenario: str                          # The question/topic to predict on
    mode: AmplificationMode
    variations_per_archetype: int = 50
    model: str = "haiku"
    fallback_model: str = "sonnet"
    max_concurrent: int = 10               # Semaphore limit
    max_budget_per_call: float = 0.05      # USD per call
    max_turns: int = 1                     # Single-turn only
    allowed_tools: list[str] = field(default_factory=list)  # Empty = no tools
    deliberation_digest: Optional[str] = None  # 500-1000 token summary for INFORMED mode
    output_dir: Path = Path(".")           # Should use ${CLAUDE_PLUGIN_DATA}/runs/{run_id}/


@dataclass
class SDKCallResult:
    """Result of a single amplification call.

    NOTE: Named SDKCallResult to avoid collision with
    engine.models.AmplificationResult (Worker A's MCP-facing model).
    """
    archetype_id: str
    variation_index: int
    prediction: Optional[PredictionPosition]
    cost_usd: float
    duration_ms: int
    is_error: bool
    error_message: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class BatchProgress:
    """Progress tracking for the amplification batch."""
    total: int
    completed: int = 0
    succeeded: int = 0
    failed: int = 0
    retried: int = 0
    total_cost_usd: float = 0.0
    start_time: float = field(default_factory=time.time)

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def calls_per_second(self) -> float:
        if self.elapsed_seconds == 0:
            return 0
        return self.completed / self.elapsed_seconds


class PersonaVariationGenerator:
    """Generates demographic and personality variations for an archetype.

    NOTE: edu_idx and axis1_idx both use n % 5, creating correlation between
    education and personality axis selection. This produces 50 unique delta
    strings but with aliasing artifacts. Future optimization: use prime-based
    stepping (e.g., edu_idx = (n * 3) % 5) for better orthogonal coverage.
    """

    # Demographic variation dimensions
    AGE_OFFSETS = [-15, -10, -5, 0, 5, 10, 15]
    LOCATIONS = [
        "major US coastal city", "US midwest city", "US southern city",
        "Western Europe", "East Asia", "South Asia", "Latin America",
        "Southeast Asia", "Middle East", "Sub-Saharan Africa",
        "Eastern Europe", "Oceania",
    ]
    EXPERIENCE_MODIFIERS = [
        "early career (2-5 years)", "mid career (8-12 years)",
        "senior (15-20 years)", "veteran (25+ years)",
    ]
    EDUCATION_MODIFIERS = [
        "self-taught / no formal degree", "bachelor's degree",
        "master's degree", "PhD or equivalent",
        "professional degree (MBA, JD, MD)",
    ]

    # Personality variation dimensions
    PERSONALITY_AXES = [
        ("optimistic", "pessimistic"),
        ("risk-tolerant", "risk-averse"),
        ("action-oriented", "analysis-oriented"),
        ("individualist", "collectivist"),
        ("early adopter", "late adopter"),
    ]

    def generate_variation_delta(
        self,
        archetype: Archetype,
        variation_index: int,
        total_variations: int,
    ) -> str:
        """Generate a variation delta string to concatenate with system_prompt.

        Uses deterministic spreading across variation dimensions to ensure
        diversity across the batch. Each variation gets a unique combination
        of demographic and personality shifts.

        NOTE: The delta is CONCATENATED with the base persona_prompt into a single
        system_prompt string (not via append_system_prompt, which does not exist
        in ClaudeAgentOptions).
        """
        n = variation_index
        age_idx = n % len(self.AGE_OFFSETS)
        loc_idx = (n // len(self.AGE_OFFSETS)) % len(self.LOCATIONS)
        exp_idx = (n // (len(self.AGE_OFFSETS) * len(self.LOCATIONS))) % len(self.EXPERIENCE_MODIFIERS)
        edu_idx = n % len(self.EDUCATION_MODIFIERS)

        # Personality: pick 2 axes to shift per variation
        axis1_idx = n % len(self.PERSONALITY_AXES)
        axis2_idx = (n + 3) % len(self.PERSONALITY_AXES)
        # Alternate between poles
        axis1_pole = self.PERSONALITY_AXES[axis1_idx][n % 2]
        axis2_pole = self.PERSONALITY_AXES[axis2_idx][(n + 1) % 2]

        age_offset = self.AGE_OFFSETS[age_idx]
        location = self.LOCATIONS[loc_idx]
        experience = self.EXPERIENCE_MODIFIERS[exp_idx]
        education = self.EDUCATION_MODIFIERS[edu_idx]

        return (
            f"VARIATION {variation_index + 1}/{total_variations}: "
            f"You are a version of this archetype with these modifications:\n"
            f"- Age: {age_offset:+d} years from the prototype\n"
            f"- Location: Based in {location}\n"
            f"- Experience: {experience}\n"
            f"- Education: {education}\n"
            f"- Personality lean: more {axis1_pole} and more {axis2_pole} "
            f"than the prototype\n\n"
            f"Apply the same analytical framework and stakeholder perspective, "
            f"but from this specific demographic and personality position. "
            f"Your core values and incentives remain the same; your weighting "
            f"of risks and opportunities may shift based on your life position."
        )


class AmplificationEngine:
    """Async engine for mass amplification via claude -p SDK."""

    def __init__(self, config: SDKAmplificationConfig):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent)
        self.progress = BatchProgress(
            total=len(config.archetypes) * config.variations_per_archetype
        )
        self.variation_gen = PersonaVariationGenerator()
        self.results: list[SDKCallResult] = []
        self._progress_callback: Optional[Callable[[BatchProgress], None]] = None

    def on_progress(self, callback: Callable[[BatchProgress], None]):
        """Register a progress callback."""
        self._progress_callback = callback

    def _validate_config(self):
        """Validate configuration before starting amplification."""
        if self.config.mode == AmplificationMode.INFORMED:
            if not self.config.deliberation_digest:
                raise ValueError(
                    "INFORMED mode requires deliberation_digest. Generate a 500-1000 token "
                    "summary of deliberation findings using a single claude -p call before "
                    "starting informed amplification. See Task D.2 orchestration flow."
                )

            # Warn if digest is too long (defeats the purpose of cost savings)
            digest_words = len(self.config.deliberation_digest.split())
            if digest_words > 1500:
                logger.warning(
                    f"Deliberation digest is {digest_words} words (~{digest_words * 1.3:.0f} tokens). "
                    f"Target is 500-1000 tokens. Long digests reduce the cost advantage over --resume."
                )

    async def run(self) -> list[SDKCallResult]:
        """Execute the full amplification batch."""
        self._validate_config()

        # Generate all call tasks
        tasks = []
        for archetype in self.config.archetypes:
            for var_idx in range(self.config.variations_per_archetype):
                tasks.append(
                    self._execute_single_call(archetype, var_idx)
                )

        # Execute with concurrency control
        self.results = await asyncio.gather(*tasks, return_exceptions=False)
        return self.results

    async def _execute_single_call(
        self,
        archetype: Archetype,
        variation_index: int,
        max_retries: int = 3,
    ) -> SDKCallResult:
        """Execute a single amplification call with retry."""
        async with self.semaphore:
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await self._do_call(archetype, variation_index)
                except ProcessError as e:
                    last_error = e
                    delay = (2 ** attempt) + (0.1 * attempt)  # Exponential backoff
                    logger.warning(
                        f"Call failed for {archetype.id} var {variation_index} "
                        f"(attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    self.progress.retried += 1
                    await asyncio.sleep(delay)

            # All retries exhausted
            self.progress.failed += 1
            self.progress.completed += 1
            self._notify_progress()
            return SDKCallResult(
                archetype_id=archetype.id,
                variation_index=variation_index,
                prediction=None,
                cost_usd=0.0,
                duration_ms=0,
                is_error=True,
                error_message=str(last_error),
            )

    async def _do_call(
        self,
        archetype: Archetype,
        variation_index: int,
    ) -> SDKCallResult:
        """Execute a single claude -p call via SDK.

        KEY DESIGN DECISIONS:
        1. system_prompt = base persona + variation delta + (optional) digest
           Concatenated into ONE string. ClaudeAgentOptions does NOT support
           append_system_prompt.
        2. allowed_tools=[] disables all tools. Amplification calls should
           ONLY produce structured JSON, never attempt tool calls.
        3. INFORMED mode uses deliberation DIGEST (500-1000 tokens) instead
           of --resume. --resume at 1500 calls with 100K+ token context would
           cost 50-100x more than baseline.
        """
        # Generate variation delta
        delta = self.variation_gen.generate_variation_delta(
            archetype, variation_index, self.config.variations_per_archetype
        )

        # Build system prompt: base + variation + (optional) digest
        system_prompt_parts = [archetype.persona_prompt, "\n\n", delta]

        # INFORMED mode: inject deliberation digest into system prompt
        if self.config.mode == AmplificationMode.INFORMED and self.config.deliberation_digest:
            system_prompt_parts.extend([
                "\n\n## Deliberation Context\n\n",
                "The following is a summary of key findings from the ensemble's ",
                "multi-round deliberation on this topic. Use these insights to ",
                "inform your prediction, but maintain your independent judgment.\n\n",
                self.config.deliberation_digest,
            ])

        full_system_prompt = "".join(system_prompt_parts)

        # Build options -- TOOL-FREE, SINGLE-TURN
        options = ClaudeAgentOptions(
            system_prompt=full_system_prompt,
            output_format={"type": "json_schema", "schema": PredictionPosition.model_json_schema()},
            model=self.config.model,
            fallback_model=self.config.fallback_model,
            max_turns=self.config.max_turns,
            max_budget_usd=self.config.max_budget_per_call,
            allowed_tools=self.config.allowed_tools,  # Default: [] (no tools)
        )

        # Execute
        start_ms = int(time.time() * 1000)
        result_msg: Optional[ResultMessage] = None
        async for msg in query(prompt=self.config.scenario, options=options):
            if isinstance(msg, ResultMessage):
                result_msg = msg

        if result_msg is None:
            raise ProcessError("No ResultMessage received", exit_code=1, stderr="")

        if result_msg.is_error:
            raise ProcessError(
                f"Call returned error: {result_msg.subtype}",
                exit_code=1,
                stderr=result_msg.result or "",
            )

        elapsed_ms = int(time.time() * 1000) - start_ms

        # Parse structured output
        prediction = PredictionPosition.model_validate(result_msg.structured_output)

        # Track progress
        cost = getattr(result_msg, "total_cost_usd", 0.0)
        self.progress.succeeded += 1
        self.progress.completed += 1
        self.progress.total_cost_usd += cost
        self._notify_progress()

        return SDKCallResult(
            archetype_id=archetype.id,
            variation_index=variation_index,
            prediction=prediction,
            cost_usd=cost,
            duration_ms=elapsed_ms,
            is_error=False,
            session_id=getattr(result_msg, "session_id", None),
        )

    def _notify_progress(self):
        """Call progress callback if registered."""
        if self._progress_callback:
            self._progress_callback(self.progress)
