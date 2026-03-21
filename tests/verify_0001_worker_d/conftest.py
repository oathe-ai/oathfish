"""Shared fixtures and paths for Worker D verification tests."""

import os
import sys

# Project root: tests/verify_0001_worker_d/ -> ../.. from this conftest
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Ensure engine is importable
sys.path.insert(0, PROJECT_ROOT)

# Canonical paths
SKILL_PATH = os.path.join(PROJECT_ROOT, "skills", "archetype-reasoning", "SKILL.md")
SDK_PATH = os.path.join(PROJECT_ROOT, "engine", "amplification_sdk.py")
ARCHETYPES_DIR = os.path.join(PROJECT_ROOT, "agents", "archetypes", "structural")
AGENTS_DIR = os.path.join(PROJECT_ROOT, "agents")
ENGINE_DIR = os.path.join(PROJECT_ROOT, "engine")
MODELS_PATH = os.path.join(PROJECT_ROOT, "engine", "models.py")

ARCHETYPE_NAMES = ["historian", "systems-thinker", "contrarian", "probabilist"]
ARCHETYPE_FILES = {n: os.path.join(ARCHETYPES_DIR, f"{n}.md") for n in ARCHETYPE_NAMES}


def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def read_archetype(name: str) -> str:
    return read_file(ARCHETYPE_FILES[name])


def read_skill() -> str:
    return read_file(SKILL_PATH)


def read_sdk() -> str:
    return read_file(SDK_PATH)
