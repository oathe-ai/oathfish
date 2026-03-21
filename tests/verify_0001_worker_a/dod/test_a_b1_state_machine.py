"""DoD A-B.1: engine/state_machine.py -- Illegal transitions rejected; history recorded; ERROR resume works.

Spec claims:
- 8-state machine (7 pipeline + INIT) + ERROR = 9 values
- LEGAL_TRANSITIONS enforced
- Any state -> ERROR allowed
- ERROR -> previous_state allowed (resume)
- previous_state stored for ERROR recovery
- state_init, state_transition, state_get, state_checkpoint, state_resume
- Write-through persistence after every mutation
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

import pytest
from engine.state_machine import StateMachineEngine, LEGAL_TRANSITIONS
from engine.models import RunPhase


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestLegalTransitions:
    """Spec: INIT->UNDERSTAND->BASELINE_AMPLIFY->DELIBERATE->AMPLIFY->SYNTHESIZE->INTERACT->COMPLETE."""

    def test_init_to_understand(self):
        assert RunPhase.UNDERSTAND in LEGAL_TRANSITIONS[RunPhase.INIT]

    def test_understand_to_baseline_amplify(self):
        assert RunPhase.BASELINE_AMPLIFY in LEGAL_TRANSITIONS[RunPhase.UNDERSTAND]

    def test_baseline_amplify_to_deliberate(self):
        assert RunPhase.DELIBERATE in LEGAL_TRANSITIONS[RunPhase.BASELINE_AMPLIFY]

    def test_deliberate_to_amplify(self):
        assert RunPhase.AMPLIFY in LEGAL_TRANSITIONS[RunPhase.DELIBERATE]

    def test_amplify_to_synthesize(self):
        assert RunPhase.SYNTHESIZE in LEGAL_TRANSITIONS[RunPhase.AMPLIFY]

    def test_synthesize_to_interact(self):
        assert RunPhase.INTERACT in LEGAL_TRANSITIONS[RunPhase.SYNTHESIZE]

    def test_interact_to_complete(self):
        assert RunPhase.COMPLETE in LEGAL_TRANSITIONS[RunPhase.INTERACT]

    def test_complete_has_no_transitions(self):
        assert LEGAL_TRANSITIONS[RunPhase.COMPLETE] == set()

    def test_all_9_states_in_transition_table(self):
        assert len(LEGAL_TRANSITIONS) == 9


class TestStateInit:
    def test_creates_run_state(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        result = run_async(engine.state_init("test-run", {"topic": "test topic"}))
        assert result["run_id"] == "test-run"
        assert result["state"] == "INIT"

    def test_persists_to_disk(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test topic"}))
        # Verify file exists on disk
        run_json = tmp_path / "test-run" / "_meta" / "run.json"
        assert run_json.exists(), "run.json not created on disk"
        with open(run_json) as f:
            data = json.load(f)
        assert data["state"] == "INIT"


class TestIllegalTransitions:
    """Spec DoD: Illegal transitions rejected."""

    def test_init_to_amplify_rejected(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        with pytest.raises(ValueError, match="Illegal transition"):
            run_async(engine.state_transition("AMPLIFY"))

    def test_init_to_complete_rejected(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        with pytest.raises(ValueError, match="Illegal transition"):
            run_async(engine.state_transition("COMPLETE"))

    def test_understand_to_deliberate_rejected(self, tmp_path):
        """Must go UNDERSTAND -> BASELINE_AMPLIFY -> DELIBERATE, not skip."""
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        run_async(engine.state_transition("UNDERSTAND"))
        with pytest.raises(ValueError, match="Illegal transition"):
            run_async(engine.state_transition("DELIBERATE"))

    def test_backward_transition_rejected(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        run_async(engine.state_transition("UNDERSTAND"))
        with pytest.raises(ValueError, match="Illegal transition"):
            run_async(engine.state_transition("INIT"))


class TestHistoryRecording:
    """Spec DoD: History recorded."""

    def test_history_includes_all_transitions(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        run_async(engine.state_transition("UNDERSTAND"))
        run_async(engine.state_transition("BASELINE_AMPLIFY"))

        result = run_async(engine.state_get())
        history = result["state_history"]
        states = [entry["state"] for entry in history]
        assert "INIT" in states
        assert "UNDERSTAND" in states
        assert "BASELINE_AMPLIFY" in states
        assert len(states) == 3

    def test_history_includes_timestamps(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        result = run_async(engine.state_get())
        for entry in result["state_history"]:
            assert "timestamp" in entry
            assert entry["timestamp"] is not None


class TestErrorRecovery:
    """Spec DoD: ERROR resume works after server restart."""

    def test_any_state_to_error(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        run_async(engine.state_transition("UNDERSTAND"))
        result = run_async(engine.state_transition("ERROR"))
        assert result["new_state"] == "ERROR"
        assert result["previous_state"] == "UNDERSTAND"

    def test_error_stores_previous_state(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        run_async(engine.state_transition("UNDERSTAND"))
        run_async(engine.state_transition("ERROR"))
        result = run_async(engine.state_get())
        assert result["state"] == "ERROR"

    def test_error_resume_to_previous_state(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        run_async(engine.state_transition("UNDERSTAND"))
        run_async(engine.state_transition("ERROR"))
        result = run_async(engine.state_transition("UNDERSTAND"))
        assert result["new_state"] == "UNDERSTAND"

    def test_error_resume_rejects_wrong_state(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        run_async(engine.state_transition("UNDERSTAND"))
        run_async(engine.state_transition("ERROR"))
        with pytest.raises(ValueError, match="Cannot transition from ERROR"):
            run_async(engine.state_transition("DELIBERATE"))

    def test_error_resume_after_server_restart(self, tmp_path):
        """Spec: ERROR resume works after server restart (read from disk)."""
        engine1 = StateMachineEngine(tmp_path)
        run_async(engine1.state_init("test-run", {"topic": "test"}))
        run_async(engine1.state_transition("UNDERSTAND"))
        run_async(engine1.state_transition("ERROR"))

        # Simulate server restart: new engine instance
        engine2 = StateMachineEngine(tmp_path)
        result = run_async(engine2.state_resume())
        assert result["state"] == "ERROR"
        assert result["previous_state"] == "UNDERSTAND"
        assert "resume_instructions" in result
        assert result["resume_instructions"] is not None

    def test_state_resume_reads_from_disk(self, tmp_path):
        """Spec: state_resume reads from disk, not memory."""
        engine1 = StateMachineEngine(tmp_path)
        run_async(engine1.state_init("test-run", {"topic": "test"}))

        engine2 = StateMachineEngine(tmp_path)
        result = run_async(engine2.state_resume())
        assert result["run_id"] == "test-run"
        assert result["state"] == "INIT"


class TestStateCheckpoint:
    def test_saves_checkpoint(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        result = run_async(engine.state_checkpoint("INIT", {"key": "value"}))
        assert "checkpoint_id" in result
        assert result["phase"] == "INIT"

    def test_checkpoint_persists_to_disk(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        run_async(engine.state_checkpoint("INIT", {"key": "value"}))

        # Read from disk
        run_json = tmp_path / "test-run" / "_meta" / "run.json"
        with open(run_json) as f:
            data = json.load(f)
        assert len(data["checkpoints"]) == 1
        assert data["checkpoints"][0]["data"]["key"] == "value"


class TestWriteThrough:
    """Spec: C-15 -- Write-through disk persistence after every mutation."""

    def test_state_transition_persists(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        run_async(engine.state_transition("UNDERSTAND"))

        # Verify directly on disk
        run_json = tmp_path / "test-run" / "_meta" / "run.json"
        with open(run_json) as f:
            data = json.load(f)
        assert data["state"] == "UNDERSTAND"

    def test_every_transition_updates_disk(self, tmp_path):
        engine = StateMachineEngine(tmp_path)
        run_async(engine.state_init("test-run", {"topic": "test"}))
        run_json = tmp_path / "test-run" / "_meta" / "run.json"

        for new_state in ["UNDERSTAND", "BASELINE_AMPLIFY", "DELIBERATE"]:
            run_async(engine.state_transition(new_state))
            with open(run_json) as f:
                data = json.load(f)
            assert data["state"] == new_state, f"Disk not updated after transition to {new_state}"
