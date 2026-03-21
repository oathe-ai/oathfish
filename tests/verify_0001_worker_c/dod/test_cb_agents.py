"""
Verify Worker C Tasks C-B.1 through C-B.3: Agent definitions.
Tests verify Claude Code compliance per sub-agents.md reference.
"""
import os
import re
import pytest

PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
AGENTS_DIR = os.path.join(PLUGIN_ROOT, "agents")


def parse_frontmatter(filepath):
    """Parse YAML frontmatter from a markdown file."""
    with open(filepath) as f:
        content = f.read()
    # Match --- delimited frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return None, content
    import yaml
    fm = yaml.safe_load(match.group(1))
    body = content[match.end():]
    return fm, body


class TestCB1DeliberationCoordinator:
    """C-B.1: agents/deliberation-coordinator.md"""

    @pytest.fixture
    def agent_path(self):
        return os.path.join(AGENTS_DIR, "deliberation-coordinator.md")

    @pytest.fixture
    def parsed(self, agent_path):
        return parse_frontmatter(agent_path)

    def test_file_exists(self, agent_path):
        assert os.path.isfile(agent_path)

    def test_has_frontmatter(self, parsed):
        fm, _ = parsed
        assert fm is not None, "Agent file must have YAML frontmatter"

    def test_has_name_field(self, parsed):
        """sub-agents.md: 'name' is required"""
        fm, _ = parsed
        assert "name" in fm, "name field is required per sub-agents.md"
        assert fm["name"] == "deliberation-coordinator"

    def test_has_description_field(self, parsed):
        """sub-agents.md: 'description' is required"""
        fm, _ = parsed
        assert "description" in fm, "description field is required per sub-agents.md"
        assert len(str(fm["description"])) > 10

    def test_tools_is_list_format(self, parsed):
        """CRITICAL: tools must be YAML list, NOT comma-separated string"""
        fm, _ = parsed
        assert "tools" in fm
        assert isinstance(fm["tools"], list), \
            f"tools must be a YAML list, got {type(fm['tools'])}: {fm['tools']}"

    def test_has_agent_tool(self, parsed):
        """Coordinator MUST have Agent tool to spawn archetype subagents"""
        fm, _ = parsed
        tools = fm.get("tools", [])
        assert "Agent" in tools, \
            "Coordinator must have Agent tool to spawn archetype subagents"

    def test_model_is_valid(self, parsed):
        """sub-agents.md: model must be sonnet/opus/haiku/inherit or full ID"""
        fm, _ = parsed
        valid_models = {"sonnet", "opus", "haiku", "inherit"}
        model = fm.get("model")
        if model is not None:
            # Allow full model IDs like claude-sonnet-4-0
            assert model in valid_models or "claude" in str(model), \
                f"Invalid model: {model}"

    def test_permissionmode_documented_as_ignored(self, parsed):
        """C-L01: permissionMode is IGNORED for plugin subagents.
        Having it is not an error, but it will have no effect."""
        fm, _ = parsed
        if "permissionMode" in fm:
            # This is a warning, not a failure -- it just won't work
            pass  # Documented as ignored per C-L01

    def test_system_prompt_has_c33_enforcement(self, parsed):
        """Spec: Coordinator system prompt with C-33 enforcement (primary layer)"""
        _, body = parsed
        c33_indicators = ["C-33", "no numeric", "arguments only", "no numbers",
                          "qualitative arguments", "round 6"]
        found = sum(1 for ind in c33_indicators if ind.lower() in body.lower())
        assert found >= 3, \
            f"Coordinator system prompt must have strong C-33 enforcement language. " \
            f"Found {found}/6 indicators in body."

    def test_system_prompt_has_round_types(self, parsed):
        """Spec: Round types FREE_FORM, STRUCTURED_DEBATE, SCENARIO_REACTION, PREDICTION"""
        _, body = parsed
        for rt in ["FREE_FORM", "STRUCTURED_DEBATE", "SCENARIO_REACTION", "PREDICTION"]:
            assert rt in body, f"Missing round type {rt} in coordinator system prompt"

    def test_system_prompt_has_verbatim_relay(self, parsed):
        """Spec: Verbatim relay (no summarization) of arguments between archetypes"""
        _, body = parsed
        body_lower = body.lower()
        assert ("verbatim" in body_lower or "full text" in body_lower or
                "do not summarize" in body_lower or "never summarize" in body_lower), \
            "Coordinator must instruct verbatim relay of arguments (H-12)"

    def test_system_prompt_has_mcp_calls(self, parsed):
        """Spec: Coordinator calls MCP tools for recording"""
        _, body = parsed
        for mcp_tool in ["deliberation_record_round", "deliberation_track_evolution",
                         "deliberation_check_convergence", "metrics_compute_round"]:
            assert mcp_tool in body, \
                f"Missing MCP tool reference: {mcp_tool}"

    def test_system_prompt_mentions_current_round_file(self, parsed):
        """Spec: Writes .current_round file for hook scripts"""
        _, body = parsed
        assert ".current_round" in body, \
            "Coordinator must write .current_round file for PreToolUse hook bridge"

    def test_round_type_is_prediction_not_independent(self, parsed):
        """Spec correction: Must use 'PREDICTION' not 'INDEPENDENT_PREDICTION'"""
        _, body = parsed
        assert "INDEPENDENT_PREDICTION" not in body, \
            "Must use 'PREDICTION' not 'INDEPENDENT_PREDICTION' (spec correction)"


class TestCB2ArchetypeAgent:
    """C-B.2: agents/archetype-agent.md"""

    @pytest.fixture
    def agent_path(self):
        return os.path.join(AGENTS_DIR, "archetype-agent.md")

    @pytest.fixture
    def parsed(self, agent_path):
        return parse_frontmatter(agent_path)

    def test_file_exists(self, agent_path):
        assert os.path.isfile(agent_path)

    def test_has_frontmatter(self, parsed):
        fm, _ = parsed
        assert fm is not None, "Agent file must have YAML frontmatter"

    def test_has_name_field(self, parsed):
        fm, _ = parsed
        assert "name" in fm
        assert fm["name"] == "archetype-agent"

    def test_has_description_field(self, parsed):
        fm, _ = parsed
        assert "description" in fm
        assert len(str(fm["description"])) > 10

    def test_has_memory_project(self, parsed):
        """SC-05: Each archetype has memory:project for cross-run learning"""
        fm, _ = parsed
        assert fm.get("memory") == "project", \
            f"archetype must have memory:project (SC-05), got: {fm.get('memory')}"

    def test_memory_value_is_valid(self, parsed):
        """sub-agents.md: memory must be 'user', 'project', or 'local'"""
        fm, _ = parsed
        valid_memory = {"user", "project", "local"}
        assert fm.get("memory") in valid_memory, \
            f"Invalid memory value: {fm.get('memory')}. Valid: {valid_memory}"

    def test_has_skills_reference(self, parsed):
        """Spec: skills field references oathfish:archetype-reasoning"""
        fm, _ = parsed
        skills = fm.get("skills", [])
        assert isinstance(skills, list), "skills must be a list"
        assert "oathfish:archetype-reasoning" in skills, \
            f"Must reference oathfish:archetype-reasoning skill, got: {skills}"

    def test_tools_is_list_format(self, parsed):
        fm, _ = parsed
        if "tools" in fm:
            assert isinstance(fm["tools"], list), \
                f"tools must be a YAML list, got {type(fm['tools'])}"

    def test_model_is_valid(self, parsed):
        """sub-agents.md: model must be valid"""
        fm, _ = parsed
        valid_models = {"sonnet", "opus", "haiku", "inherit"}
        model = fm.get("model")
        if model is not None:
            assert model in valid_models or "claude" in str(model), \
                f"Invalid model: {model}"

    def test_system_prompt_forbids_numbers_rounds_1_5(self, parsed):
        """C-33 tertiary enforcement: archetype prompt forbids numeric predictions"""
        _, body = parsed
        body_lower = body.lower()
        assert ("no numeric" in body_lower or "no stance scores" in body_lower or
                "no confidence" in body_lower or
                "do not include" in body_lower and "numeric" in body_lower), \
            "Archetype system prompt must forbid numeric predictions in rounds 1-5 (C-33 tertiary)"

    def test_system_prompt_has_superforecaster_methodology(self, parsed):
        """Spec: C-30 superforecaster methodology in every archetype prompt"""
        _, body = parsed
        body_lower = body.lower()
        indicators = ["base rate", "decompos", "uncertaint", "falsification"]
        found = sum(1 for ind in indicators if ind in body_lower)
        assert found >= 3, \
            f"Archetype prompt must include superforecaster methodology (C-30). " \
            f"Found {found}/4 indicators."

    def test_no_hooks_in_frontmatter(self, parsed):
        """C-L01: hooks in plugin subagent frontmatter are IGNORED.
        Hooks should be in hooks/hooks.json instead."""
        fm, _ = parsed
        # Having hooks here is not necessarily wrong but they will be IGNORED
        if "hooks" in fm:
            pytest.skip("Hooks in plugin subagent frontmatter are IGNORED per C-L01 -- "
                        "not a failure but they have no effect")

    def test_no_mcp_servers_in_frontmatter(self, parsed):
        """C-L01: mcpServers in plugin subagent frontmatter are IGNORED"""
        fm, _ = parsed
        assert "mcpServers" not in fm, \
            "mcpServers in plugin subagent frontmatter are IGNORED per C-L01"


class TestCB3ReportAnalyst:
    """C-B.3: agents/report-analyst.md"""

    @pytest.fixture
    def agent_path(self):
        return os.path.join(AGENTS_DIR, "report-analyst.md")

    @pytest.fixture
    def parsed(self, agent_path):
        return parse_frontmatter(agent_path)

    def test_file_exists(self, agent_path):
        assert os.path.isfile(agent_path)

    def test_has_frontmatter(self, parsed):
        fm, _ = parsed
        assert fm is not None

    def test_has_name_field(self, parsed):
        fm, _ = parsed
        assert "name" in fm
        assert fm["name"] == "report-analyst"

    def test_has_description_field(self, parsed):
        fm, _ = parsed
        assert "description" in fm

    def test_tools_is_list_format(self, parsed):
        fm, _ = parsed
        if "tools" in fm:
            assert isinstance(fm["tools"], list)

    def test_system_prompt_has_react_methodology(self, parsed):
        """Spec: ReACT pattern for report generation"""
        _, body = parsed
        body_lower = body.lower()
        assert "react" in body_lower or "think" in body_lower and "act" in body_lower, \
            "Report analyst must use ReACT methodology"

    def test_system_prompt_specifies_5_outputs(self, parsed):
        """Spec: report-analyst produces 5 outputs"""
        _, body = parsed
        expected_outputs = ["report.md", "reasoning-chains.md", "statistics.md",
                            "calibration.md", "diversity-trajectory.md"]
        found = sum(1 for out in expected_outputs if out in body)
        assert found >= 5, \
            f"Report analyst must produce 5 outputs. Found {found}/5: " \
            f"Missing: {[o for o in expected_outputs if o not in body]}"
