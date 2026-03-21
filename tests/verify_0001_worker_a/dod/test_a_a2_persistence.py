"""DoD A-A.2: engine/persistence.py -- Atomic write verified; crash leaves original intact.

Spec claims:
- atomic_write_json using temp+rename pattern
- os.fsync() before rename
- try/except with temp file cleanup
- read_json returns None if file does not exist
- ensure_run_dir creates subdirectories
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from engine.persistence import atomic_write_json, read_json, ensure_run_dir
from engine.models import RunConfig


class TestAtomicWriteJson:
    """Spec: Atomic write via temp+rename, os.fsync()."""

    def test_writes_dict_successfully(self, tmp_path):
        target = tmp_path / "test.json"
        data = {"key": "value", "number": 42}
        atomic_write_json(target, data)
        assert target.exists()
        with open(target) as f:
            loaded = json.load(f)
        assert loaded == data

    def test_writes_pydantic_model_successfully(self, tmp_path):
        target = tmp_path / "config.json"
        config = RunConfig(topic="AI regulation")
        atomic_write_json(target, config)
        assert target.exists()
        with open(target) as f:
            loaded = json.load(f)
        assert loaded["topic"] == "AI regulation"

    def test_writes_list_successfully(self, tmp_path):
        target = tmp_path / "list.json"
        data = [1, 2, 3, "test"]
        atomic_write_json(target, data)
        assert target.exists()
        with open(target) as f:
            loaded = json.load(f)
        assert loaded == data

    def test_creates_parent_directories(self, tmp_path):
        target = tmp_path / "deep" / "nested" / "dir" / "test.json"
        atomic_write_json(target, {"test": True})
        assert target.exists()

    def test_overwrites_existing_file(self, tmp_path):
        target = tmp_path / "test.json"
        atomic_write_json(target, {"version": 1})
        atomic_write_json(target, {"version": 2})
        with open(target) as f:
            loaded = json.load(f)
        assert loaded["version"] == 2

    def test_original_preserved_on_write_failure(self, tmp_path):
        """Spec DoD: crash during write leaves original intact."""
        target = tmp_path / "test.json"
        original = {"original": True, "important": "data"}
        atomic_write_json(target, original)

        # Simulate failure during write by patching os.replace to raise
        with patch("engine.persistence.os.replace", side_effect=IOError("disk full")):
            try:
                atomic_write_json(target, {"corrupted": True})
            except IOError:
                pass

        # Original should still be intact
        with open(target) as f:
            loaded = json.load(f)
        assert loaded == original

    def test_no_temp_files_left_on_failure(self, tmp_path):
        """Spec: try/except with temp file cleanup."""
        target = tmp_path / "test.json"
        atomic_write_json(target, {"initial": True})

        with patch("engine.persistence.os.replace", side_effect=IOError("disk full")):
            try:
                atomic_write_json(target, {"corrupted": True})
            except IOError:
                pass

        # No .tmp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0, f"Temp files left behind: {tmp_files}"

    def test_uses_fsync(self, tmp_path):
        """Spec: os.fsync() before rename."""
        target = tmp_path / "test.json"
        with patch("engine.persistence.os.fsync") as mock_fsync:
            atomic_write_json(target, {"test": True})
            assert mock_fsync.called, "os.fsync() was not called during atomic write"


class TestReadJson:
    """Spec: Returns None if file does not exist."""

    def test_returns_none_for_nonexistent(self, tmp_path):
        result = read_json(tmp_path / "nonexistent.json")
        assert result is None

    def test_reads_existing_file(self, tmp_path):
        target = tmp_path / "test.json"
        data = {"key": "value"}
        with open(target, "w") as f:
            json.dump(data, f)
        result = read_json(target)
        assert result == data


class TestEnsureRunDir:
    """Spec: Create and return run directory structure."""

    def test_creates_run_directory(self, tmp_path):
        run_dir = ensure_run_dir(tmp_path, "run-001")
        assert run_dir.exists()
        assert run_dir == tmp_path / "run-001"

    def test_creates_subdirectories(self, tmp_path):
        run_dir = ensure_run_dir(tmp_path, "run-001")
        expected_subdirs = [
            "_meta", "understanding", "graph", "deliberation",
            "amplification", "amplification/results", "amplification/prompts",
            "synthesis", "team",
        ]
        for subdir in expected_subdirs:
            subpath = run_dir / subdir
            assert subpath.is_dir(), f"Missing subdirectory: {subdir}"

    def test_idempotent(self, tmp_path):
        """Calling twice should not raise."""
        run_dir1 = ensure_run_dir(tmp_path, "run-001")
        run_dir2 = ensure_run_dir(tmp_path, "run-001")
        assert run_dir1 == run_dir2
