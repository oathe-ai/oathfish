"""Write-through persistence layer for OathFish MCP server.

Every engine mutation MUST use these functions to ensure:
- C-15: State persists to disk after every mutation
- C-23: All state changes flush to disk immediately
- Crash safety: Atomic writes via temp+rename
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from pydantic import BaseModel


def atomic_write_json(path: Path, data: BaseModel | dict | list) -> None:
    """Atomically write JSON data to path.

    Uses write-to-temp-then-rename pattern for POSIX atomicity.
    Ensures parent directories exist.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(data, BaseModel):
        content = data.model_dump_json(indent=2)
    else:
        content = json.dumps(data, indent=2, default=str)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        suffix=".tmp",
        prefix=".oathfish_",
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Force flush to disk
        os.replace(tmp_path, str(path))  # Atomic on POSIX
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically write plain text to path.

    Same temp+rename pattern as atomic_write_json but for non-JSON content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        suffix=".tmp",
        prefix=".oathfish_",
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_json(path: Path) -> dict | list | None:
    """Read JSON from path. Returns None if file does not exist."""
    if not path.exists():
        return None
    with open(path, "r") as f:
        return json.load(f)


def ensure_run_dir(data_dir: Path, run_id: str) -> Path:
    """Create and return the run directory structure."""
    run_dir = data_dir / run_id
    for subdir in [
        "_meta",
        "understanding",
        "graph",
        "deliberation",
        "amplification",
        "amplification/results",
        "amplification/prompts",
        "synthesis",
        "team",
    ]:
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)
    return run_dir
