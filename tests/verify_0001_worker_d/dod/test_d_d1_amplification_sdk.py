"""DoD D-D.1: engine/amplification_sdk.py -- Core amplification engine.
DoD D-A.1: Import PredictionPosition from engine.models (NOT redefine).
"""

import ast
import os
import re
import pytest

from tests.verify_0001_worker_d.conftest import SDK_PATH, read_sdk


def _parse_ast():
    return ast.parse(read_sdk())


class TestImportNotRedefine:
    def test_imports_from_engine_models(self):
        s = read_sdk()
        assert re.search(r"from\s+\.models\s+import.*PredictionPosition", s) or \
               re.search(r"from\s+engine\.models\s+import.*PredictionPosition", s)

    def test_imports_archetype_from_engine_models(self):
        s = read_sdk()
        assert re.search(r"from\s+\.models\s+import.*Archetype", s) or \
               re.search(r"from\s+engine\.models\s+import.*Archetype", s)

    def test_no_local_prediction_position_class(self):
        classes = [n.name for n in ast.walk(_parse_ast()) if isinstance(n, ast.ClassDef)]
        assert "PredictionPosition" not in classes

    def test_no_local_archetype_class(self):
        classes = [n.name for n in ast.walk(_parse_ast()) if isinstance(n, ast.ClassDef)]
        assert "Archetype" not in classes


class TestRequiredClasses:
    def _classes(self):
        return [n.name for n in ast.walk(_parse_ast()) if isinstance(n, ast.ClassDef)]

    def test_amplification_mode(self): assert "AmplificationMode" in self._classes()
    def test_sdk_amplification_config(self): assert "SDKAmplificationConfig" in self._classes()
    def test_sdk_call_result(self): assert "SDKCallResult" in self._classes()
    def test_batch_progress(self): assert "BatchProgress" in self._classes()
    def test_persona_variation_generator(self): assert "PersonaVariationGenerator" in self._classes()
    def test_amplification_engine(self): assert "AmplificationEngine" in self._classes()

    def test_exactly_six_classes(self):
        c = self._classes()
        assert len(c) == 6, f"Expected 6, found {len(c)}: {c}"


class TestAmplificationMode:
    def test_has_baseline_value(self):
        assert re.search(r'BASELINE\s*=\s*["\']baseline["\']', read_sdk())

    def test_has_informed_value(self):
        assert re.search(r'INFORMED\s*=\s*["\']informed["\']', read_sdk())


class TestConfigFields:
    def test_has_allowed_tools_empty_default(self):
        assert re.search(r"allowed_tools.*default_factory\s*=\s*list|allowed_tools.*=.*\[\]", read_sdk())

    def test_has_max_turns_1(self):
        assert re.search(r"max_turns.*=\s*1", read_sdk())

    def test_has_deliberation_digest(self):
        assert "deliberation_digest" in read_sdk()

    def test_has_max_concurrent_10(self):
        assert re.search(r"max_concurrent.*=\s*10", read_sdk())

    def test_has_model_default_haiku(self):
        assert re.search(r'model.*=\s*["\']haiku["\']', read_sdk())

    def test_has_fallback_model(self):
        assert "fallback_model" in read_sdk()


class TestSemaphore:
    def test_semaphore_created(self):
        assert "asyncio.Semaphore" in read_sdk()

    def test_semaphore_used_as_context_manager(self):
        assert re.search(r"async\s+with\s+self\.semaphore", read_sdk())


class TestExponentialBackoff:
    def test_retry_loop_exists(self):
        assert re.search(r"for\s+attempt\s+in\s+range\(.*retr", read_sdk())

    def test_exponential_delay(self):
        assert re.search(r"2\s*\*\*\s*attempt", read_sdk())

    def test_asyncio_sleep_in_retry(self):
        assert "asyncio.sleep" in read_sdk()


class TestSchemaEnforcement:
    def test_model_json_schema_called(self):
        assert "model_json_schema()" in read_sdk()


class TestNoResume:
    def test_no_resume_as_sdk_parameter(self):
        """D-H05: --resume must NOT be passed to ClaudeAgentOptions or query().
        References in docstrings/log messages explaining 'NOT --resume' are acceptable.
        The real danger is passing resume_session_id or --resume as an actual parameter."""
        source = read_sdk()
        # Must not pass resume_session_id or resume as a parameter to ClaudeAgentOptions
        assert not re.search(r"resume_session_id\s*=", source), (
            "Must NOT pass resume_session_id to ClaudeAgentOptions (D-H05)"
        )
        # Must not use --resume as a CLI flag
        assert not re.search(r'["\']--resume["\']', source), (
            "Must NOT pass '--resume' as a string argument (D-H05)"
        )

    def test_digest_approach_documented(self):
        assert re.search(r"(?i)digest", read_sdk())


class TestSystemPromptConcatenation:
    def test_no_append_system_prompt_as_parameter(self):
        """append_system_prompt does NOT exist in ClaudeAgentOptions.
        Docstring mentions explaining this are acceptable. Actual parameter usage is not."""
        source = read_sdk()
        # Must not pass append_system_prompt= as a keyword argument
        assert not re.search(r"append_system_prompt\s*=", source), (
            "Must NOT use append_system_prompt= as parameter (it does not exist)"
        )

    def test_system_prompt_concatenation(self):
        assert re.search(r'"".join|system_prompt_parts', read_sdk())


class TestCostTracking:
    def test_cost_field_exists(self): assert "cost_usd" in read_sdk()
    def test_total_cost_tracked(self): assert "total_cost_usd" in read_sdk()
    def test_max_budget_per_call(self): assert "max_budget" in read_sdk()


class TestPersonaVariationGenerator:
    def test_has_generate_variation_delta_method(self):
        for node in ast.walk(_parse_ast()):
            if isinstance(node, ast.ClassDef) and node.name == "PersonaVariationGenerator":
                methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                assert "generate_variation_delta" in methods
                return
        pytest.fail("PersonaVariationGenerator not found")

    def test_has_demographic_dimensions(self):
        s = read_sdk()
        for dim in ["AGE_OFFSETS", "LOCATIONS", "EXPERIENCE_MODIFIERS", "EDUCATION_MODIFIERS"]:
            assert dim in s, f"Missing dimension: {dim}"

    def test_has_personality_dimensions(self):
        assert "PERSONALITY_AXES" in read_sdk()

    def test_aliasing_documented(self):
        assert re.search(r"(?i)alias", read_sdk())


class TestDualModeValidation:
    def test_informed_requires_digest(self):
        assert re.search(r"INFORMED.*deliberation_digest|mode.*INFORMED.*digest", read_sdk(), re.DOTALL)

    def test_validation_raises_on_missing_digest(self):
        """Validate that INFORMED mode without digest raises ValueError."""
        # The raise and 'digest' are on different lines, so use DOTALL
        assert re.search(r"raise\s+ValueError\(.*digest", read_sdk(), re.DOTALL), (
            "INFORMED mode must raise ValueError when digest is missing"
        )
