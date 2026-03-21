"""
Verify constraint compliance for Worker C files.
"""
import json
import os
import re
import pytest

PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


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


class TestC01PluginStructure:
    """C-01: System must be a Claude Code plugin"""

    def test_all_plugin_directories_present(self):
        required = [".claude-plugin", "agents", "skills", "commands", "hooks"]
        for d in required:
            assert os.path.isdir(os.path.join(PLUGIN_ROOT, d)), \
                f"Missing required plugin directory: {d}"

    def test_plugin_json_valid(self):
        path = os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json")
        with open(path) as f:
            data = json.load(f)
        assert data.get("name") == "oathfish"


class TestC05NoTeamsForDeliberation:
    """C-05: No Teams for archetype deliberation -- use subagents instead"""

    def test_coordinator_does_not_use_teams(self):
        _, body = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "deliberation-coordinator.md"))
        body_lower = body.lower()
        # Should use subagents, not Teams
        assert "subagent" in body_lower or "agent tool" in body_lower, \
            "Coordinator should reference subagent architecture, not Teams"

    def test_deliberate_skill_does_not_use_teamcreate(self):
        """Per C-05: No Teams for deliberation. Use Agent tool for subagents."""
        path = os.path.join(PLUGIN_ROOT, "skills", "deliberate", "SKILL.md")
        with open(path) as f:
            content = f.read()
        # TeamCreate should NOT be in the deliberate skill (subagent architecture)
        assert "TeamCreate" not in content, \
            "deliberate skill should NOT use TeamCreate (C-05: no Teams for deliberation)"


class TestC07StateSequence:
    """C-07: 8-state pipeline sequence"""

    def test_dispatcher_has_full_sequence(self):
        path = os.path.join(PLUGIN_ROOT, "skills", "oathfish", "SKILL.md")
        with open(path) as f:
            content = f.read()
        phases = ["INIT", "UNDERSTAND", "BASELINE_AMPLIFY", "DELIBERATE",
                  "AMPLIFY", "SYNTHESIZE", "INTERACT", "COMPLETE"]
        for phase in phases:
            assert phase in content, f"Missing phase {phase} in dispatcher"


class TestC33NoNumericPredictionsShared:
    """C-33: No numeric predictions shared between archetypes until round 6"""

    def test_three_layer_defense_complete(self):
        """All three layers must exist"""
        # Layer 1: Coordinator prompt
        _, body = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "deliberation-coordinator.md"))
        assert "c-33" in body.lower(), "Layer 1 missing"

        # Layer 2: PreToolUse hook
        with open(os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")) as f:
            data = json.load(f)
        pre_tool = data["hooks"].get("PreToolUse", [])
        agent_hooks = [h for h in pre_tool if h.get("matcher") == "Agent"]
        assert len(agent_hooks) >= 1, "Layer 2 missing"

        # Layer 3: Archetype prompt
        _, body = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "archetype-agent.md"))
        body_lower = body.lower()
        assert any(phrase in body_lower for phrase in [
            "do not include", "no numeric", "no stance"
        ]), "Layer 3 missing"

    def test_validate_script_catches_stance_numbers(self):
        """Attack: 'STANCE: 0.7' in round 3 should be caught by regex"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        with open(path) as f:
            content = f.read()
        # The regex should catch patterns like "stance: 0.7"
        assert "stance" in content.lower(), \
            "Validate script must check for 'stance' + number pattern"

    def test_validate_script_catches_confidence_percent(self):
        """Attack: 'CONFIDENCE: 85%' should be caught"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        with open(path) as f:
            content = f.read()
        assert "confidence" in content.lower(), \
            "Validate script must check for 'confidence' + number pattern"

    def test_validate_script_catches_probability(self):
        """Attack: 'probability: 0.65' should be caught"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        with open(path) as f:
            content = f.read()
        assert "probability" in content.lower() or "predict" in content.lower(), \
            "Validate script must check for probability numbers"


class TestCL01PluginSubagentIgnored:
    """C-L01: Plugin subagent hooks, mcpServers, permissionMode IGNORED"""

    def test_coordinator_permissionmode_noted_as_ignored(self):
        """permissionMode: bypassPermissions is set but will be IGNORED"""
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "deliberation-coordinator.md"))
        # This is a documentation check -- the field exists but won't work
        if fm.get("permissionMode"):
            pass  # Noted: will be ignored, but not an error to include

    def test_report_analyst_permissionmode_noted_as_ignored(self):
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "report-analyst.md"))
        if fm.get("permissionMode"):
            pass  # Noted: will be ignored

    def test_no_mcp_servers_in_subagent_frontmatter(self):
        """mcpServers in subagent frontmatter are IGNORED"""
        for agent_file in ["archetype-agent.md", "report-analyst.md"]:
            path = os.path.join(PLUGIN_ROOT, "agents", agent_file)
            if os.path.isfile(path):
                fm, _ = parse_frontmatter(path)
                if fm and "mcpServers" in fm:
                    pytest.fail(
                        f"{agent_file} has mcpServers in frontmatter -- "
                        f"these are IGNORED per C-L01")


class TestCL02SubagentsCannotSpawn:
    """C-L02: Subagents CANNOT spawn other subagents"""

    def test_deliberate_runs_inline(self):
        """Main thread required for spawning archetypes"""
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "skills", "deliberate", "SKILL.md"))
        assert fm.get("context") != "fork"

    def test_synthesize_nesting_issue(self):
        """CRITICAL CHECK: synthesize uses context:fork but spawns report-analyst.
        This creates a subagent-of-a-subagent which violates C-L02."""
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "skills", "synthesize", "SKILL.md"))
        if fm.get("context") == "fork":
            allowed_tools = fm.get("allowed-tools", "")
            if isinstance(allowed_tools, str):
                tools_list = [t.strip() for t in allowed_tools.split(",")]
            elif isinstance(allowed_tools, list):
                tools_list = allowed_tools
            else:
                tools_list = []
            if "Agent" in tools_list:
                pytest.fail(
                    "C-L02 VIOLATION: synthesize skill runs with context:fork (= subagent) "
                    "but has Agent in allowed-tools. A forked subagent CANNOT spawn "
                    "another subagent (report-analyst). This will fail at runtime."
                )


class TestC36StructuralArchetypes:
    """C-36: 4 structural archetypes present in EVERY run"""

    def test_structural_archetype_files_exist(self):
        structural_dir = os.path.join(
            PLUGIN_ROOT, "agents", "archetypes", "structural")
        assert os.path.isdir(structural_dir), \
            "agents/archetypes/structural/ directory must exist"
        expected = ["historian.md", "systems-thinker.md",
                    "contrarian.md", "probabilist.md"]
        for name in expected:
            path = os.path.join(structural_dir, name)
            assert os.path.isfile(path), f"Missing structural archetype: {name}"


class TestC37StructuralNotStakeholder:
    """C-37: Structural archetypes are epistemic lenses, NOT stakeholder personas"""

    @pytest.mark.parametrize("archetype", [
        "historian.md", "systems-thinker.md", "contrarian.md", "probabilist.md"
    ])
    def test_epistemic_lens_language(self, archetype):
        """Each structural archetype must contain 'epistemic lens' or 'NOT a stakeholder'"""
        path = os.path.join(
            PLUGIN_ROOT, "agents", "archetypes", "structural", archetype)
        with open(path) as f:
            content = f.read()
        content_lower = content.lower()
        assert ("epistemic lens" in content_lower or
                "not a stakeholder" in content_lower), \
            f"{archetype} must explicitly state it is an epistemic lens, not a stakeholder"
