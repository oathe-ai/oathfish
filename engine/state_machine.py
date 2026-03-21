"""State machine engine for OathFish run lifecycle management.

8-state machine (7 pipeline phases + INIT) with ERROR recovery.
5 MCP tools: state_init, state_transition, state_get, state_checkpoint, state_resume.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    CheckpointData,
    RunConfig,
    RunPhase,
    RunState,
    StateHistoryEntry,
)
from .persistence import atomic_write_json, atomic_write_text, ensure_run_dir, read_json

# Legal state transitions
# 9 states total: 7 pipeline phases + INIT + ERROR
# Any state can transition to ERROR. ERROR resumes to previous_state.
LEGAL_TRANSITIONS: dict[RunPhase, set[RunPhase]] = {
    RunPhase.INIT: {RunPhase.UNDERSTAND},
    RunPhase.UNDERSTAND: {RunPhase.BASELINE_AMPLIFY},
    RunPhase.BASELINE_AMPLIFY: {RunPhase.DELIBERATE},
    RunPhase.DELIBERATE: {RunPhase.AMPLIFY},
    RunPhase.AMPLIFY: {RunPhase.SYNTHESIZE},
    RunPhase.SYNTHESIZE: {RunPhase.INTERACT},
    RunPhase.INTERACT: {RunPhase.COMPLETE},
    RunPhase.COMPLETE: set(),
    RunPhase.ERROR: set(),  # Dynamic: resolved via previous_state
}


class StateMachineEngine:
    """Run lifecycle management with 8-state state machine."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._current_run: RunState | None = None

    def _run_json_path(self) -> Path:
        assert self._current_run is not None
        return Path(self._current_run.run_dir) / "_meta" / "run.json"

    def _persist(self) -> None:
        """Write-through: flush current run state to disk."""
        assert self._current_run is not None
        atomic_write_json(self._run_json_path(), self._current_run)

    def _load_from_disk(self) -> RunState | None:
        """Load run state from the most recent run directory."""
        if not self._data_dir.exists():
            return None
        # Find most recent run directory
        run_dirs = sorted(self._data_dir.iterdir()) if self._data_dir.is_dir() else []
        for run_dir in reversed(run_dirs):
            run_json = run_dir / "_meta" / "run.json"
            data = read_json(run_json)
            if data is not None:
                return RunState.model_validate(data)
        return None

    async def state_init(self, run_id: str, config: dict) -> dict:
        """Creates run directory structure and run.json."""
        run_config = RunConfig.model_validate(config)
        now = datetime.now(timezone.utc).isoformat()
        run_dir = ensure_run_dir(self._data_dir, run_id)

        self._current_run = RunState(
            run_id=run_id,
            state=RunPhase.INIT,
            config=run_config,
            state_history=[StateHistoryEntry(state=RunPhase.INIT, timestamp=now)],
            created_at=now,
            run_dir=str(run_dir),
        )
        self._persist()

        # Write .active_run so shell scripts and skill preprocessors can find the current run
        active_run_path = self._data_dir.parent / ".active_run"
        atomic_write_text(active_run_path, run_id)

        return {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "state": RunPhase.INIT.value,
            "created_at": now,
        }

    async def state_transition(self, new_state: str) -> dict:
        """Validates transition is legal, records in run.json with timestamp."""
        if self._current_run is None:
            self._current_run = self._load_from_disk()
        if self._current_run is None:
            raise ValueError("No active run. Call state_init first.")

        target = RunPhase(new_state)
        current = self._current_run.state
        now = datetime.now(timezone.utc).isoformat()

        # Handle ERROR transition: any state -> ERROR
        if target == RunPhase.ERROR:
            self._current_run.previous_state = current
            self._current_run.state = RunPhase.ERROR
            self._current_run.state_history.append(
                StateHistoryEntry(state=RunPhase.ERROR, timestamp=now)
            )
            self._persist()
            return {
                "previous_state": current.value,
                "new_state": RunPhase.ERROR.value,
                "timestamp": now,
            }

        # Handle ERROR resume: ERROR -> previous_state
        if current == RunPhase.ERROR:
            if self._current_run.previous_state is not None and target == self._current_run.previous_state:
                self._current_run.state = target
                self._current_run.previous_state = None
                self._current_run.state_history.append(
                    StateHistoryEntry(state=target, timestamp=now)
                )
                self._persist()
                return {
                    "previous_state": RunPhase.ERROR.value,
                    "new_state": target.value,
                    "timestamp": now,
                }
            raise ValueError(
                f"Cannot transition from ERROR to {target.value}. "
                f"Can only resume to {self._current_run.previous_state.value if self._current_run.previous_state else 'None'}."
            )

        # Normal transition validation
        allowed = LEGAL_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(
                f"Illegal transition: {current.value} -> {target.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        prev = current.value
        self._current_run.state = target
        self._current_run.state_history.append(
            StateHistoryEntry(state=target, timestamp=now)
        )
        self._persist()

        return {
            "previous_state": prev,
            "new_state": target.value,
            "timestamp": now,
        }

    async def state_get(self) -> dict:
        """Returns current run state, config, and full state history."""
        if self._current_run is None:
            self._current_run = self._load_from_disk()
        if self._current_run is None:
            return {"error": "No active run", "state": None}

        return {
            "run_id": self._current_run.run_id,
            "state": self._current_run.state.value,
            "config": self._current_run.config.model_dump(mode="json"),
            "state_history": [
                {"state": e.state.value, "timestamp": e.timestamp}
                for e in self._current_run.state_history
            ],
        }

    async def state_checkpoint(self, phase: str, data: dict) -> dict:
        """Saves checkpoint data for the current phase."""
        if self._current_run is None:
            self._current_run = self._load_from_disk()
        if self._current_run is None:
            raise ValueError("No active run. Call state_init first.")

        now = datetime.now(timezone.utc).isoformat()
        checkpoint_id = f"ckpt-{uuid.uuid4().hex[:8]}"

        checkpoint = CheckpointData(
            checkpoint_id=checkpoint_id,
            phase=RunPhase(phase),
            data=data,
            timestamp=now,
        )
        self._current_run.checkpoints.append(checkpoint)
        self._persist()

        return {
            "checkpoint_id": checkpoint_id,
            "phase": phase,
            "timestamp": now,
        }

    async def state_resume(self) -> dict:
        """Returns last valid state and checkpoint data (reads from disk, not memory)."""
        # Always read from disk to support restart recovery
        run_state = self._load_from_disk()
        if run_state is None:
            return {"error": "No run found on disk", "state": None}

        self._current_run = run_state

        last_checkpoint = None
        if run_state.checkpoints:
            last_checkpoint = run_state.checkpoints[-1].model_dump(mode="json")

        resume_instructions = None
        if run_state.state == RunPhase.ERROR and run_state.previous_state:
            resume_instructions = (
                f"Run is in ERROR state. Previous state was {run_state.previous_state.value}. "
                f"Call state_transition('{run_state.previous_state.value}') to resume."
            )

        return {
            "run_id": run_state.run_id,
            "state": run_state.state.value,
            "previous_state": run_state.previous_state.value if run_state.previous_state else None,
            "checkpoint": last_checkpoint,
            "resume_instructions": resume_instructions,
        }


def register_tools(app, data_dir: Path) -> None:
    """Register state machine MCP tools on the server."""
    engine = StateMachineEngine(data_dir)

    @app.tool()
    async def state_init(run_id: str, config: dict) -> dict:
        """Initialize a new OathFish run with directory structure and state tracking.

        Args:
            run_id: Unique run identifier
            config: RunConfig fields (topic, archetype_count, deliberation_rounds, etc.)
        """
        return await engine.state_init(run_id, config)

    @app.tool()
    async def state_transition(new_state: str) -> dict:
        """Transition the run to a new phase. Validates the transition is legal.

        Args:
            new_state: Target RunPhase (UNDERSTAND, BASELINE_AMPLIFY, DELIBERATE, AMPLIFY, SYNTHESIZE, INTERACT, COMPLETE, ERROR)
        """
        return await engine.state_transition(new_state)

    @app.tool()
    async def state_get() -> dict:
        """Get current run state, config, and full state history."""
        return await engine.state_get()

    @app.tool()
    async def state_checkpoint(phase: str, data: dict) -> dict:
        """Save checkpoint data for the current phase (enables resume after crash).

        Args:
            phase: Current RunPhase
            data: Arbitrary checkpoint data to persist
        """
        return await engine.state_checkpoint(phase, data)

    @app.tool()
    async def state_resume() -> dict:
        """Resume from last known state by reading from disk. Use after server restart."""
        return await engine.state_resume()
