"""
Verify Success Criteria SC-02 through SC-05 (Worker C scope).
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


class TestSC02PluginLoads:
    """SC-02: Plugin loads and /oathfish command appears in skill menu"""

    def test_plugin_json_exists(self):
        path = os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json")
        assert os.path.isfile(path)

    def test_oathfish_command_exists(self):
        """The /oathfish command file must exist"""
        path = os.path.join(PLUGIN_ROOT, "commands", "oathfish.md")
        assert os.path.isfile(path)

    def test_oathfish_skill_exists(self):
        """The oathfish skill must exist"""
        path = os.path.join(PLUGIN_ROOT, "skills", "oathfish", "SKILL.md")
        assert os.path.isfile(path)

    def test_oathfish_command_has_name(self):
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "commands", "oathfish.md"))
        assert fm is not None
        assert fm.get("name") == "oathfish"

    def test_oathfish_skill_has_name(self):
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "skills", "oathfish", "SKILL.md"))
        assert fm is not None
        assert fm.get("name") == "oathfish"

    def test_mcp_json_exists(self):
        path = os.path.join(PLUGIN_ROOT, ".mcp.json")
        assert os.path.isfile(path)

    def test_hooks_json_exists(self):
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        assert os.path.isfile(path)

    def test_all_required_directories_exist(self):
        """Plugin structure requires agents/, skills/, commands/, hooks/"""
        for subdir in ["agents", "skills", "commands", "hooks",
                       ".claude-plugin", "scripts"]:
            path = os.path.join(PLUGIN_ROOT, subdir)
            assert os.path.isdir(path), f"Missing directory: {subdir}"


class TestSC03CoordinatorSpawns30:
    """SC-03: Coordinator can spawn 30 archetype subagents per round via Agent tool"""

    def test_coordinator_has_agent_tool(self):
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "deliberation-coordinator.md"))
        assert "Agent" in fm.get("tools", []), \
            "Coordinator must have Agent tool to spawn subagents"

    def test_archetype_agent_template_exists(self):
        path = os.path.join(PLUGIN_ROOT, "agents", "archetype-agent.md")
        assert os.path.isfile(path)

    def test_deliberate_skill_references_30_archetypes(self):
        path = os.path.join(PLUGIN_ROOT, "skills", "deliberate", "SKILL.md")
        with open(path) as f:
            content = f.read()
        assert "30" in content, \
            "Deliberate skill must reference 30 archetypes"

    def test_deliberate_skill_runs_inline(self):
        """Subagent spawning requires main thread context"""
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "skills", "deliberate", "SKILL.md"))
        assert fm.get("context") != "fork", \
            "deliberate skill MUST run inline for subagent spawning"

    def test_4_structural_archetypes_exist(self):
        """C-36: 4 structural archetypes present"""
        structural_dir = os.path.join(PLUGIN_ROOT, "agents", "archetypes", "structural")
        expected = ["historian.md", "systems-thinker.md",
                    "contrarian.md", "probabilist.md"]
        for name in expected:
            path = os.path.join(structural_dir, name)
            assert os.path.isfile(path), f"Missing structural archetype: {name}"


class TestSC04C33Enforcement:
    """SC-04: C-33 enforcement prevents numeric predictions in rounds 1-5.
    Three-layer defense must exist."""

    def test_layer1_coordinator_prompt(self):
        """Primary: Coordinator system prompt forbids relaying numbers"""
        _, body = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "deliberation-coordinator.md"))
        body_lower = body.lower()
        assert "c-33" in body_lower, \
            "Layer 1: Coordinator must mention C-33"
        assert any(phrase in body_lower for phrase in [
            "no numeric predictions", "arguments only", "no numbers",
            "no stance scores", "qualitative arguments only"
        ]), "Layer 1: Coordinator must forbid numeric predictions"

    def test_layer2_pretooluse_hook(self):
        """Secondary: PreToolUse hook on Agent in hooks.json"""
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            data = json.load(f)
        pre_tool = data["hooks"].get("PreToolUse", [])
        agent_hooks = [h for h in pre_tool if h.get("matcher") == "Agent"]
        assert len(agent_hooks) >= 1, \
            "Layer 2: Missing PreToolUse on Agent hook"
        cmd = agent_hooks[0]["hooks"][0].get("command", "")
        assert "validate-no-numbers" in cmd, \
            "Layer 2: Hook must run validate-no-numbers.sh"

    def test_layer2_script_exists_and_executable(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        assert os.path.isfile(path), "validate-no-numbers.sh must exist"
        assert os.access(path, os.X_OK), "validate-no-numbers.sh must be executable"

    def test_layer2_script_blocks_with_exit_2(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        with open(path) as f:
            content = f.read()
        assert "exit 2" in content, \
            "Layer 2: script must exit 2 to block (hooks-guide.md)"

    def test_layer3_archetype_prompt(self):
        """Tertiary: Archetype system prompt forbids numeric predictions"""
        _, body = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "archetype-agent.md"))
        body_lower = body.lower()
        assert any(phrase in body_lower for phrase in [
            "do not include", "no numeric", "no stance scores",
            "no confidence percentages"
        ]), "Layer 3: Archetype prompt must forbid numeric predictions in rounds 1-5"

    def test_validate_script_has_round_exception(self):
        """Round 6+ must be allowed through"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        with open(path) as f:
            content = f.read()
        assert ".current_round" in content, \
            "Script must read round number for round 6 exception"
        assert any(x in content for x in ["-ge 6", ">= 6"]), \
            "Script must allow round 6+ through"


class TestSC05ArchetypeMemoryProject:
    """SC-05: Each archetype has memory:project for cross-run learning"""

    def test_archetype_agent_has_memory_project(self):
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "archetype-agent.md"))
        assert fm.get("memory") == "project", \
            f"archetype-agent must have memory:project, got: {fm.get('memory')}"

    def test_memory_value_is_valid(self):
        """sub-agents.md: memory must be user/project/local"""
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "archetype-agent.md"))
        valid = {"user", "project", "local"}
        assert fm.get("memory") in valid

    def test_archetype_prompt_mentions_cross_run(self):
        """Prompt should discuss cross-run memory usage"""
        _, body = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "archetype-agent.md"))
        body_lower = body.lower()
        assert "cross-run" in body_lower or "persistent memory" in body_lower or \
            "memory across" in body_lower, \
            "Archetype prompt should explain cross-run memory usage"
