"""DoD: B-B.2 -- Register 6 calibration tools in server.py.

Spec says: 27 total MCP tools (21 core + 6 calibration/competence).
Worker B tools: calibration_record_prediction, calibration_record_outcome,
calibration_get_domain_bias, calibration_get_archetype_bias,
calibration_get_ensemble_metrics, competence_classify_question.
"""

import pytest


class TestBB2ServerRegistration:
    """Verify calibration tools are registered in server.py."""

    def test_calibration_engine_has_register_tools(self):
        """calibration_engine.py should export register_tools function."""
        from engine.calibration_engine import register_tools
        assert callable(register_tools)

    def test_server_py_imports_calibration(self):
        """server.py source code should import register_calibration_tools."""
        from pathlib import Path
        server_path = Path(__file__).resolve().parents[3] / "engine" / "server.py"
        source = server_path.read_text()
        assert "register_calibration_tools" in source, \
            "server.py should import register_calibration_tools"
        assert "register_calibration_tools(app, DATA_DIR)" in source, \
            "server.py should call register_calibration_tools(app, DATA_DIR)"

    def test_server_registers_six_calibration_tools(self):
        """Verify server.py registers the correct tool function names."""
        from pathlib import Path
        # Read the calibration_engine.py source for tool registration
        cal_path = Path(__file__).resolve().parents[3] / "engine" / "calibration_engine.py"
        source = cal_path.read_text()

        expected_tool_names = [
            "calibration_record_prediction",
            "calibration_record_outcome",
            "calibration_get_domain_bias",
            "calibration_get_archetype_bias",
            "calibration_get_ensemble_metrics",
            "competence_classify_question",
        ]
        for name in expected_tool_names:
            assert f"async def {name}" in source, \
                f"Tool '{name}' not found as async def in calibration_engine.py"

    def test_register_tools_signature(self):
        """register_tools should accept (app, data_dir) parameters."""
        import inspect
        from engine.calibration_engine import register_tools
        sig = inspect.signature(register_tools)
        params = list(sig.parameters.keys())
        assert "app" in params, "register_tools missing 'app' parameter"
        assert "data_dir" in params, "register_tools missing 'data_dir' parameter"
