"""
Integration smoke tests for Worker C orchestration layer.
"""
import json
import os
import re
import subprocess
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


class TestPluginStructureIntegrity:
    """Verify the complete plugin structure is coherent."""

    def test_all_22_worker_c_files_exist(self):
        """Ledger claims 22 files were created. Verify all exist."""
        expected_files = [
            ".claude-plugin/plugin.json",
            ".mcp.json",
            "hooks/hooks.json",
            "scripts/validate-no-numbers.sh",
            "scripts/oathfish-init.sh",
            "scripts/oathfish-reinject-state.sh",
            "scripts/get-state.sh",
            "scripts/setup.sh",
            "agents/deliberation-coordinator.md",
            "agents/archetype-agent.md",
            "agents/report-analyst.md",
            "skills/oathfish/SKILL.md",
            "skills/understand/SKILL.md",
            "skills/baseline-amplify/SKILL.md",
            "skills/deliberate/SKILL.md",
            "skills/amplify/SKILL.md",
            "skills/synthesize/SKILL.md",
            "skills/interact/SKILL.md",
            "commands/oathfish.md",
            "commands/oathfish-chat.md",
            "commands/oathfish-inject.md",
            "commands/oathfish-calibrate.md",
        ]
        missing = []
        for rel_path in expected_files:
            full = os.path.join(PLUGIN_ROOT, rel_path)
            if not os.path.isfile(full):
                missing.append(rel_path)
        assert not missing, f"Missing Worker C files: {missing}"

    def test_all_json_files_valid(self):
        """All JSON files must parse without error."""
        json_files = [
            ".claude-plugin/plugin.json",
            ".mcp.json",
            "hooks/hooks.json",
        ]
        for rel_path in json_files:
            full = os.path.join(PLUGIN_ROOT, rel_path)
            with open(full) as f:
                try:
                    json.load(f)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {rel_path}: {e}")

    def test_all_shell_scripts_valid_syntax(self):
        """All .sh files must pass bash -n."""
        scripts = [
            "scripts/validate-no-numbers.sh",
            "scripts/oathfish-init.sh",
            "scripts/oathfish-reinject-state.sh",
            "scripts/get-state.sh",
            "scripts/setup.sh",
        ]
        for rel_path in scripts:
            full = os.path.join(PLUGIN_ROOT, rel_path)
            result = subprocess.run(
                ["bash", "-n", full], capture_output=True, text=True)
            assert result.returncode == 0, \
                f"Syntax error in {rel_path}: {result.stderr}"

    def test_all_shell_scripts_executable(self):
        """All .sh files must be executable."""
        scripts = [
            "scripts/validate-no-numbers.sh",
            "scripts/oathfish-init.sh",
            "scripts/oathfish-reinject-state.sh",
            "scripts/get-state.sh",
            "scripts/setup.sh",
        ]
        for rel_path in scripts:
            full = os.path.join(PLUGIN_ROOT, rel_path)
            assert os.access(full, os.X_OK), \
                f"{rel_path} is not executable"

    def test_all_agent_files_have_frontmatter(self):
        """All agent .md files in agents/ (top-level) must have valid frontmatter."""
        agents_dir = os.path.join(PLUGIN_ROOT, "agents")
        for filename in os.listdir(agents_dir):
            if filename.endswith(".md"):
                full = os.path.join(agents_dir, filename)
                fm, _ = parse_frontmatter(full)
                assert fm is not None, \
                    f"Agent {filename} missing YAML frontmatter"
                assert "name" in fm, \
                    f"Agent {filename} missing 'name' field"
                assert "description" in fm, \
                    f"Agent {filename} missing 'description' field"

    def test_all_skill_files_have_frontmatter(self):
        """All SKILL.md files must have valid frontmatter."""
        skills_dir = os.path.join(PLUGIN_ROOT, "skills")
        for skill_name in os.listdir(skills_dir):
            skill_path = os.path.join(skills_dir, skill_name, "SKILL.md")
            if os.path.isfile(skill_path):
                fm, _ = parse_frontmatter(skill_path)
                assert fm is not None, \
                    f"Skill {skill_name} missing YAML frontmatter"

    def test_all_command_files_have_frontmatter(self):
        """All command .md files must have valid frontmatter."""
        cmds_dir = os.path.join(PLUGIN_ROOT, "commands")
        for filename in os.listdir(cmds_dir):
            if filename.endswith(".md"):
                full = os.path.join(cmds_dir, filename)
                fm, _ = parse_frontmatter(full)
                assert fm is not None, \
                    f"Command {filename} missing YAML frontmatter"
                assert "name" in fm, \
                    f"Command {filename} missing 'name' field"


class TestSkillContextCorrectness:
    """Verify that context:fork vs inline is correct for each skill."""

    def test_skills_with_fork(self):
        """understand, baseline-amplify, amplify, synthesize should have context:fork"""
        forked_skills = ["understand", "baseline-amplify", "amplify", "synthesize"]
        for skill_name in forked_skills:
            fm, _ = parse_frontmatter(
                os.path.join(PLUGIN_ROOT, "skills", skill_name, "SKILL.md"))
            assert fm.get("context") == "fork", \
                f"Skill {skill_name} must have context:fork"

    def test_skills_without_fork(self):
        """oathfish, deliberate, interact must run inline (no context:fork)"""
        inline_skills = ["oathfish", "deliberate", "interact"]
        for skill_name in inline_skills:
            fm, _ = parse_frontmatter(
                os.path.join(PLUGIN_ROOT, "skills", skill_name, "SKILL.md"))
            assert fm.get("context") != "fork", \
                f"Skill {skill_name} must run INLINE (no context:fork)"

    def test_archetype_reasoning_no_fork(self):
        """archetype-reasoning must be inline (preloaded into subagents)"""
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "skills", "archetype-reasoning", "SKILL.md"))
        assert fm.get("context") != "fork", \
            "archetype-reasoning must NOT have context:fork"


class TestCrossComponentReferences:
    """Verify cross-component references are consistent."""

    def test_archetype_agent_references_existing_skill(self):
        """archetype-agent references oathfish:archetype-reasoning skill"""
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "archetype-agent.md"))
        skills = fm.get("skills", [])
        # "oathfish:archetype-reasoning" -- 'oathfish' is the plugin namespace
        ref = "oathfish:archetype-reasoning"
        assert ref in skills, \
            f"archetype-agent must reference {ref}"
        # Verify the skill exists
        skill_path = os.path.join(
            PLUGIN_ROOT, "skills", "archetype-reasoning", "SKILL.md")
        assert os.path.isfile(skill_path), \
            "Referenced skill archetype-reasoning/SKILL.md must exist"

    def test_hooks_reference_existing_scripts(self):
        """All hook commands must reference existing scripts"""
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            data = json.load(f)
        for event_hooks in data["hooks"].values():
            for hook_entry in event_hooks:
                for hook in hook_entry.get("hooks", []):
                    cmd = hook.get("command", "")
                    if "${CLAUDE_PLUGIN_ROOT}" in cmd:
                        # Replace variable with actual path for checking
                        resolved = cmd.replace("${CLAUDE_PLUGIN_ROOT}", PLUGIN_ROOT)
                        assert os.path.isfile(resolved), \
                            f"Hook references missing script: {cmd} -> {resolved}"

    def test_deliberate_skill_references_archetype_agent(self):
        """deliberate skill should reference archetype-agent for spawning"""
        path = os.path.join(PLUGIN_ROOT, "skills", "deliberate", "SKILL.md")
        with open(path) as f:
            content = f.read()
        assert "archetype" in content.lower()

    def test_synthesize_skill_references_report_analyst(self):
        """synthesize skill should reference report-analyst"""
        path = os.path.join(PLUGIN_ROOT, "skills", "synthesize", "SKILL.md")
        with open(path) as f:
            content = f.read()
        assert "report-analyst" in content


class TestC33EndToEnd:
    """End-to-end C-33 enforcement chain verification."""

    def test_c33_defense_chain_complete(self):
        """Verify all three layers of C-33 defense exist and are connected."""
        # Layer 1: Coordinator prompt
        _, coord_body = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "deliberation-coordinator.md"))

        # Layer 2: PreToolUse hook -> validate-no-numbers.sh
        with open(os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")) as f:
            hooks = json.load(f)

        # Layer 3: Archetype prompt
        _, arch_body = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "archetype-agent.md"))

        # Verify Layer 1
        assert "c-33" in coord_body.lower(), "Layer 1: Coordinator missing C-33 reference"

        # Verify Layer 2
        pre_tool = hooks["hooks"].get("PreToolUse", [])
        agent_hooks = [h for h in pre_tool if h.get("matcher") == "Agent"]
        assert len(agent_hooks) >= 1, "Layer 2: Missing PreToolUse on Agent"
        script_cmd = agent_hooks[0]["hooks"][0].get("command", "")
        assert "validate-no-numbers" in script_cmd, "Layer 2: Wrong script"

        # Verify the script exists and is executable
        script_path = script_cmd.replace("${CLAUDE_PLUGIN_ROOT}", PLUGIN_ROOT)
        assert os.path.isfile(script_path), "Layer 2: Script file missing"
        assert os.access(script_path, os.X_OK), "Layer 2: Script not executable"

        # Verify script uses exit 2 for blocking
        with open(script_path) as f:
            script_content = f.read()
        assert "exit 2" in script_content, "Layer 2: Script must exit 2 to block"

        # Verify Layer 3
        arch_lower = arch_body.lower()
        assert any(phrase in arch_lower for phrase in [
            "do not include", "no numeric", "no stance"
        ]), "Layer 3: Archetype missing numeric prohibition"

    def test_deliberate_skill_enforces_c33(self):
        """The deliberate skill itself must have C-33 enforcement instructions"""
        path = os.path.join(PLUGIN_ROOT, "skills", "deliberate", "SKILL.md")
        with open(path) as f:
            content = f.read()
        assert "c-33" in content.lower() or "C-33" in content
