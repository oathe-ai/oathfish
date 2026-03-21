#!/bin/bash
cd /Users/shezmalik/Projects/Oathe/oathfish

echo "=== Step 1: Python Version ==="
.venv/bin/python --version

echo ""
echo "=== Step 2: Pydantic Version ==="
.venv/bin/python -c "import pydantic; print(pydantic.__version__)"

echo ""
echo "=== Step 3a: Import engine.models ==="
.venv/bin/python -c "from engine.models import *; print('OK')"

echo ""
echo "=== Step 3b: Import engine.server ==="
.venv/bin/python -c "from engine.server import *; print('OK')"

echo ""
echo "=== Step 3c: Import engine.calibration_engine ==="
.venv/bin/python -c "from engine.calibration_engine import *; print('OK')"

echo ""
echo "=== Step 4a: Run tests/ ==="
.venv/bin/python -m pytest tests/ -v --tb=short 2>&1 | tail -80

echo ""
echo "=== Step 4b: Run tests/verify_0001_worker_a/ ==="
.venv/bin/python -m pytest tests/verify_0001_worker_a/ -v --tb=short 2>&1 | tail -80

echo ""
echo "=== Step 4c: Run tests/verify_0001_worker_b/ ==="
.venv/bin/python -m pytest tests/verify_0001_worker_b/ -v --tb=short 2>&1 | tail -80

echo ""
echo "=== Step 4d: Run tests/verify_0001_worker_d/ ==="
.venv/bin/python -m pytest tests/verify_0001_worker_d/ -v --tb=short 2>&1 | tail -80

echo ""
echo "=== Step 5: MCP Server Startup ==="
timeout 3 .venv/bin/python engine/server.py 2>&1; echo "Exit code: $?"
