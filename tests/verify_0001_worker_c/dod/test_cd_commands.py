"""
Verify Worker C Tasks C-D.1 through C-D.4: Command definitions.
"""
import os
import re
import pytest

PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
COMMANDS_DIR = os.path.join(PLUGIN_ROOT, "commands")


def parse_frontmatter(filepath):
    with open(filepath) as f:
        content = f.read()
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return None, content
    import yaml
    fm = yaml.safe_load(match.group(1))
    body = content[match.end():]
    return fm, body


class TestCD1OathfishCommand:
    """C-D.1: commands/oathfish.md"""

    @pytest.fixture
    def cmd_path(self):
        return os.path.join(COMMANDS_DIR, "oathfish.md")

    @pytest.fixture
    def parsed(self, cmd_path):
        return parse_frontmatter(cmd_path)

    def test_file_exists(self, cmd_path):
        assert os.path.isfile(cmd_path)

    def test_has_frontmatter(self, parsed):
        fm, _ = parsed
        assert fm is not None

    def test_has_name(self, parsed):
        fm, _ = parsed
        assert fm.get("name") == "oathfish"

    def test_has_description(self, parsed):
        fm, _ = parsed
        assert "description" in fm

    def test_has_argument_hint(self, parsed):
        fm, _ = parsed
        assert "argument-hint" in fm

    def test_uses_arguments(self, cmd_path):
        with open(cmd_path) as f:
            content = f.read()
        assert "$ARGUMENTS" in content


class TestCD2OathfishChat:
    """C-D.2: commands/oathfish-chat.md"""

    @pytest.fixture
    def cmd_path(self):
        return os.path.join(COMMANDS_DIR, "oathfish-chat.md")

    @pytest.fixture
    def parsed(self, cmd_path):
        return parse_frontmatter(cmd_path)

    def test_file_exists(self, cmd_path):
        assert os.path.isfile(cmd_path)

    def test_has_frontmatter(self, parsed):
        fm, _ = parsed
        assert fm is not None

    def test_has_name(self, parsed):
        fm, _ = parsed
        assert fm.get("name") == "oathfish-chat"

    def test_has_argument_hint(self, parsed):
        fm, _ = parsed
        assert "argument-hint" in fm

    def test_routes_to_archetype_or_report(self, cmd_path):
        with open(cmd_path) as f:
            content = f.read()
        assert "--archetype" in content
        assert "--report" in content


class TestCD3OathfishInject:
    """C-D.3: commands/oathfish-inject.md"""

    @pytest.fixture
    def cmd_path(self):
        return os.path.join(COMMANDS_DIR, "oathfish-inject.md")

    @pytest.fixture
    def parsed(self, cmd_path):
        return parse_frontmatter(cmd_path)

    def test_file_exists(self, cmd_path):
        assert os.path.isfile(cmd_path)

    def test_has_frontmatter(self, parsed):
        fm, _ = parsed
        assert fm is not None

    def test_has_name(self, parsed):
        fm, _ = parsed
        assert fm.get("name") == "oathfish-inject"

    def test_has_disable_model_invocation(self, parsed):
        """Spec: disable-model-invocation for inject command"""
        fm, _ = parsed
        assert fm.get("disable-model-invocation") is True, \
            "oathfish-inject should have disable-model-invocation: true"


class TestCD4OathfishCalibrate:
    """C-D.4: commands/oathfish-calibrate.md"""

    @pytest.fixture
    def cmd_path(self):
        return os.path.join(COMMANDS_DIR, "oathfish-calibrate.md")

    @pytest.fixture
    def parsed(self, cmd_path):
        return parse_frontmatter(cmd_path)

    def test_file_exists(self, cmd_path):
        assert os.path.isfile(cmd_path)

    def test_has_frontmatter(self, parsed):
        fm, _ = parsed
        assert fm is not None

    def test_has_name(self, parsed):
        fm, _ = parsed
        assert fm.get("name") == "oathfish-calibrate"

    def test_has_disable_model_invocation(self, parsed):
        fm, _ = parsed
        assert fm.get("disable-model-invocation") is True

    def test_references_calibration_operations(self, cmd_path):
        with open(cmd_path) as f:
            content = f.read()
        assert "record-outcome" in content or "record_outcome" in content
        assert "forecastbench" in content.lower()
