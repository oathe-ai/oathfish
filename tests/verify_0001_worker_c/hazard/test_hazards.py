"""
Verify Worker C hazard mitigations C-H01 through C-H14.
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


class TestCH01ContextPressure:
    """C-H01: Coordinator context pressure (180 payloads / 6 rounds)
    Mitigation: MCP-as-external-memory; compact hook re-injects state"""

    def test_compact_hook_exists(self):
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            data = json.load(f)
        compact = [h for h in data["hooks"].get("SessionStart", [])
                   if h.get("matcher") == "compact"]
        assert len(compact) >= 1, "Missing compact recovery hook"

    def test_reinject_script_provides_recovery(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "oathfish-reinject-state.sh")
        with open(path) as f:
            content = f.read()
        assert "state_get" in content or "state" in content.lower(), \
            "Recovery script must provide state recovery guidance"

    def test_coordinator_has_compaction_recovery(self):
        _, body = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "deliberation-coordinator.md"))
        assert "compact" in body.lower(), \
            "Coordinator must have compaction recovery instructions"


class TestCH02MCPOutputExceeds:
    """C-H02: MCP output exceeds 25K (position map with 30 archetypes)
    Mitigation: Paginated queries"""

    def test_max_mcp_output_tokens_configured(self):
        path = os.path.join(PLUGIN_ROOT, ".mcp.json")
        with open(path) as f:
            data = json.load(f)
        env = data["mcpServers"]["oathfish-engine"].get("env", {})
        assert "MAX_MCP_OUTPUT_TOKENS" in env, \
            "Must set MAX_MCP_OUTPUT_TOKENS for H-02 defense"


class TestCH03C33BrokenInFrontmatter:
    """C-H03: Plugin subagent hooks IGNORED -- C-33 broken in frontmatter
    Mitigation: Three-layer defense"""

    def test_archetype_agent_no_hooks_in_frontmatter(self):
        """C-L01: hooks in plugin subagent frontmatter are IGNORED.
        Enforcement must be in hooks/hooks.json instead."""
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "archetype-agent.md"))
        if "hooks" in fm:
            pytest.fail("Hooks in archetype-agent frontmatter will be IGNORED per C-L01. "
                        "C-33 enforcement must be in hooks/hooks.json, not here.")

    def test_c33_enforcement_in_hooks_json(self):
        """C-33 must be enforced via hooks/hooks.json PreToolUse"""
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            data = json.load(f)
        pre_tool = data["hooks"].get("PreToolUse", [])
        agent_hooks = [h for h in pre_tool if h.get("matcher") == "Agent"]
        assert len(agent_hooks) >= 1, \
            "C-33 must be enforced via PreToolUse on Agent in hooks.json"


class TestCH04MCPServerAlive:
    """C-H04: MCP server must be alive for state transitions
    Mitigation: setup.sh verification; oathfish skill checks state_get()"""

    def test_setup_verifies_server(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "setup.sh")
        with open(path) as f:
            content = f.read()
        assert "server" in content.lower(), \
            "setup.sh must verify MCP server starts"

    def test_dispatcher_checks_state(self):
        path = os.path.join(PLUGIN_ROOT, "skills", "oathfish", "SKILL.md")
        with open(path) as f:
            content = f.read()
        assert "state_get" in content or "get-state" in content, \
            "Dispatcher must check state (implying MCP is alive)"


class TestCH05MCPNamespacing:
    """C-H05: allowed-tools MCP namespacing syntax unverified
    Mitigation: Test with one skill first; fallback to permissive"""

    def test_skills_have_allowed_tools(self):
        """Check that skills with allowed-tools don't use unverified MCP namespacing"""
        skills_dir = os.path.join(PLUGIN_ROOT, "skills")
        for skill_name in os.listdir(skills_dir):
            skill_path = os.path.join(skills_dir, skill_name, "SKILL.md")
            if os.path.isfile(skill_path):
                fm, _ = parse_frontmatter(skill_path)
                if fm and "allowed-tools" in fm:
                    tools = fm["allowed-tools"]
                    # Check for MCP-namespaced tools that might not work
                    if isinstance(tools, str):
                        if "mcp__" in tools:
                            pytest.fail(
                                f"Skill {skill_name} uses mcp__ namespace in allowed-tools "
                                f"which is unverified per C-H05")


class TestCH06RoundNumberBridge:
    """C-H06: Round number unavailable to hooks
    Mitigation: File-based bridge: coordinator writes .current_round"""

    def test_coordinator_writes_round_file(self):
        _, body = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "deliberation-coordinator.md"))
        assert ".current_round" in body, \
            "Coordinator must write .current_round file"

    def test_deliberate_skill_writes_round_file(self):
        path = os.path.join(PLUGIN_ROOT, "skills", "deliberate", "SKILL.md")
        with open(path) as f:
            content = f.read()
        assert ".current_round" in content

    def test_validate_script_reads_round_file(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        with open(path) as f:
            content = f.read()
        assert ".current_round" in content


class TestCH12ArgumentRelayFidelity:
    """C-H12: Argument relay fidelity degradation
    Mitigation: System prompt: 'Pass FULL text, do NOT summarize'"""

    def test_coordinator_instructs_verbatim(self):
        _, body = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "agents", "deliberation-coordinator.md"))
        body_lower = body.lower()
        assert any(phrase in body_lower for phrase in [
            "full text", "verbatim", "do not summarize", "never summarize",
            "not summarize"
        ]), "Coordinator must instruct verbatim argument relay"


class TestCH14NestingProblem:
    """C-H14: Nesting problem: dispatcher cannot launch coordinator as subagent of subagent
    RESOLVED: deliberate skill runs inline"""

    def test_deliberate_skill_is_inline(self):
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "skills", "deliberate", "SKILL.md"))
        assert fm.get("context") != "fork", \
            "deliberate MUST be inline to avoid nesting problem"

    def test_synthesize_spawns_report_analyst_from_fork(self):
        """POTENTIAL ISSUE: synthesize runs in context:fork but spawns report-analyst.
        Per C-L02, subagents cannot spawn other subagents. If context:fork creates
        a subagent, it cannot spawn report-analyst."""
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "skills", "synthesize", "SKILL.md"))
        if fm.get("context") == "fork":
            # Check if it tries to use Agent tool
            skill_path = os.path.join(PLUGIN_ROOT, "skills", "synthesize", "SKILL.md")
            with open(skill_path) as f:
                content = f.read()
            if "@report-analyst" in content or "Agent" in str(fm.get("allowed-tools", "")):
                pytest.fail(
                    "ARCHITECTURAL ISSUE: synthesize skill runs in context:fork "
                    "(which creates a subagent) but tries to spawn @report-analyst. "
                    "Per C-L02, subagents CANNOT spawn other subagents. "
                    "Either: (1) synthesize must run inline, or "
                    "(2) report-analyst must not be spawned as a subagent from here."
                )
