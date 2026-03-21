"""
Verify Worker C Task C-A.1 through C-A.6: Plugin scaffold, hooks, and scripts.
Tests generated from spec BEFORE reading implementation.
"""
import json
import os
import subprocess
import yaml
import pytest

PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


class TestCA1PluginJson:
    """C-A.1: .claude-plugin/plugin.json -- Plugin manifest"""

    def test_file_exists(self):
        path = os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json")
        assert os.path.isfile(path), "plugin.json must exist"

    def test_valid_json(self):
        path = os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json")
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_has_required_fields(self):
        """Spec: name='oathfish', version='0.1.0', author='Oathe'"""
        path = os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json")
        with open(path) as f:
            data = json.load(f)
        assert data.get("name") == "oathfish"
        assert "version" in data
        assert data.get("author") == "Oathe"

    def test_has_description(self):
        path = os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json")
        with open(path) as f:
            data = json.load(f)
        assert "description" in data and len(data["description"]) > 10


class TestCA2McpJson:
    """C-A.2: .mcp.json -- MCP server config"""

    def test_file_exists(self):
        path = os.path.join(PLUGIN_ROOT, ".mcp.json")
        assert os.path.isfile(path), ".mcp.json must exist"

    def test_valid_json(self):
        path = os.path.join(PLUGIN_ROOT, ".mcp.json")
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_has_mcp_servers_key(self):
        path = os.path.join(PLUGIN_ROOT, ".mcp.json")
        with open(path) as f:
            data = json.load(f)
        assert "mcpServers" in data

    def test_oathfish_engine_server_defined(self):
        path = os.path.join(PLUGIN_ROOT, ".mcp.json")
        with open(path) as f:
            data = json.load(f)
        assert "oathfish-engine" in data["mcpServers"]

    def test_uses_stdio_transport(self):
        path = os.path.join(PLUGIN_ROOT, ".mcp.json")
        with open(path) as f:
            data = json.load(f)
        server = data["mcpServers"]["oathfish-engine"]
        assert server.get("type") == "stdio"

    def test_uses_python3_not_python(self):
        """Spec: command should use 'python3' (not 'python')"""
        path = os.path.join(PLUGIN_ROOT, ".mcp.json")
        with open(path) as f:
            data = json.load(f)
        server = data["mcpServers"]["oathfish-engine"]
        assert server.get("command") == "python3", \
            f"Expected 'python3', got '{server.get('command')}'"

    def test_oathfish_data_dir_uses_plugin_data(self):
        """Spec correction: OATHFISH_DATA_DIR must use CLAUDE_PLUGIN_DATA, NOT CLAUDE_PLUGIN_ROOT.
        CLAUDE_PLUGIN_ROOT is wiped on plugin update."""
        path = os.path.join(PLUGIN_ROOT, ".mcp.json")
        with open(path) as f:
            data = json.load(f)
        env = data["mcpServers"]["oathfish-engine"].get("env", {})
        data_dir = env.get("OATHFISH_DATA_DIR", "")
        assert "CLAUDE_PLUGIN_DATA" in data_dir, \
            f"OATHFISH_DATA_DIR must reference CLAUDE_PLUGIN_DATA, got: {data_dir}"
        assert "CLAUDE_PLUGIN_ROOT" not in data_dir, \
            f"OATHFISH_DATA_DIR must NOT reference CLAUDE_PLUGIN_ROOT (wiped on update)"

    def test_max_mcp_output_tokens_set(self):
        """Spec: MAX_MCP_OUTPUT_TOKENS=50000 for H-07 defense-in-depth"""
        path = os.path.join(PLUGIN_ROOT, ".mcp.json")
        with open(path) as f:
            data = json.load(f)
        env = data["mcpServers"]["oathfish-engine"].get("env", {})
        assert env.get("MAX_MCP_OUTPUT_TOKENS") == "50000", \
            "MAX_MCP_OUTPUT_TOKENS must be '50000'"

    def test_args_reference_server(self):
        """Server must be invocable via the args"""
        path = os.path.join(PLUGIN_ROOT, ".mcp.json")
        with open(path) as f:
            data = json.load(f)
        server = data["mcpServers"]["oathfish-engine"]
        args = server.get("args", [])
        # Either direct file path or -m module invocation is acceptable
        args_str = " ".join(args)
        assert "server" in args_str.lower() or "engine" in args_str.lower(), \
            f"Args must reference the engine/server, got: {args}"


class TestCA3HooksJson:
    """C-A.3: hooks/hooks.json -- SessionStart + PreToolUse hooks"""

    def test_file_exists(self):
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        assert os.path.isfile(path), "hooks/hooks.json must exist"

    def test_valid_json(self):
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_has_hooks_key(self):
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            data = json.load(f)
        assert "hooks" in data

    def test_session_start_startup_hook(self):
        """Spec: SessionStart 'startup' -> oathfish-init.sh"""
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            data = json.load(f)
        session_start = data["hooks"].get("SessionStart", [])
        startup_hooks = [h for h in session_start if h.get("matcher") == "startup"]
        assert len(startup_hooks) >= 1, "Missing SessionStart startup hook"
        cmd = startup_hooks[0]["hooks"][0].get("command", "")
        assert "oathfish-init" in cmd

    def test_session_start_compact_hook(self):
        """Spec: SessionStart 'compact' -> oathfish-reinject-state.sh"""
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            data = json.load(f)
        session_start = data["hooks"].get("SessionStart", [])
        compact_hooks = [h for h in session_start if h.get("matcher") == "compact"]
        assert len(compact_hooks) >= 1, "Missing SessionStart compact hook"
        cmd = compact_hooks[0]["hooks"][0].get("command", "")
        assert "reinject" in cmd

    def test_pretooluse_agent_hook(self):
        """Spec: PreToolUse on Agent -> validate-no-numbers.sh (C-33 secondary)"""
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            data = json.load(f)
        pre_tool = data["hooks"].get("PreToolUse", [])
        agent_hooks = [h for h in pre_tool if h.get("matcher") == "Agent"]
        assert len(agent_hooks) >= 1, "Missing PreToolUse Agent hook for C-33"
        cmd = agent_hooks[0]["hooks"][0].get("command", "")
        assert "validate-no-numbers" in cmd

    def test_hook_commands_use_plugin_root(self):
        """Spec: All hook scripts use ${CLAUDE_PLUGIN_ROOT}"""
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            data = json.load(f)
        for event_hooks in data["hooks"].values():
            for hook_entry in event_hooks:
                for hook in hook_entry.get("hooks", []):
                    cmd = hook.get("command", "")
                    if cmd:
                        assert "${CLAUDE_PLUGIN_ROOT}" in cmd, \
                            f"Hook command must use ${{CLAUDE_PLUGIN_ROOT}}, got: {cmd}"

    def test_hooks_use_valid_event_names(self):
        """Verify event names match hooks-guide.md valid events"""
        valid_events = {
            "SessionStart", "UserPromptSubmit", "PreToolUse",
            "PermissionRequest", "PostToolUse", "PostToolUseFailure",
            "Notification", "SubagentStart", "SubagentStop", "Stop",
            "TeammateIdle", "TaskCompleted", "InstructionsLoaded",
            "ConfigChange", "WorktreeCreate", "WorktreeRemove",
            "PreCompact", "PostCompact", "Elicitation",
            "ElicitationResult", "SessionEnd"
        }
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            data = json.load(f)
        for event_name in data["hooks"].keys():
            assert event_name in valid_events, \
                f"Invalid hook event name: {event_name}. Valid: {valid_events}"

    def test_hook_type_is_command(self):
        """All hooks should be type 'command'"""
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            data = json.load(f)
        for event_hooks in data["hooks"].values():
            for hook_entry in event_hooks:
                for hook in hook_entry.get("hooks", []):
                    hook_type = hook.get("type")
                    assert hook_type in ("command", "prompt", "agent", "http"), \
                        f"Invalid hook type: {hook_type}"

    def test_session_start_matchers_valid(self):
        """Per hooks-guide.md: SessionStart matcher filters how session started.
        Valid: 'startup', 'resume', 'clear', 'compact'"""
        valid_matchers = {"startup", "resume", "clear", "compact"}
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            data = json.load(f)
        for hook_entry in data["hooks"].get("SessionStart", []):
            matcher = hook_entry.get("matcher", "")
            if matcher:
                assert matcher in valid_matchers, \
                    f"Invalid SessionStart matcher: {matcher}. Valid: {valid_matchers}"


class TestCA4ValidateNoNumbers:
    """C-A.4: scripts/validate-no-numbers.sh -- C-33 enforcement"""

    def test_file_exists(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        assert os.path.isfile(path)

    def test_is_executable(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        assert os.access(path, os.X_OK), "validate-no-numbers.sh must be executable"

    def test_syntax_valid(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        result = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_uses_jq_for_json_parsing(self):
        """Script must use jq (not sed/awk) for robust JSON parsing"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        with open(path) as f:
            content = f.read()
        assert "jq" in content, "validate-no-numbers.sh must use jq for JSON parsing"

    def test_reads_tool_input_prompt(self):
        """Script must extract prompt from PreToolUse hook input"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        with open(path) as f:
            content = f.read()
        assert "tool_input" in content, \
            "Must read from tool_input (PreToolUse hook format)"

    def test_uses_exit_2_for_block(self):
        """Per hooks-guide.md: exit 2 = block the action"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        with open(path) as f:
            content = f.read()
        assert "exit 2" in content, "Must use exit 2 to block (per hooks-guide.md)"

    def test_reads_current_round_file(self):
        """Script must check current round via file bridge (C-H06)"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        with open(path) as f:
            content = f.read()
        assert ".current_round" in content, \
            "Must read .current_round file for round-based exception"

    def test_allows_round_6_numbers(self):
        """Round 6+ must allow numeric predictions"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        with open(path) as f:
            content = f.read()
        # Must have logic that exits 0 (allow) for round >= 6
        assert "-ge 6" in content or ">= 6" in content or "round_n >= 6" in content.lower() or \
            ("-ge" in content and "6" in content), \
            "Must allow numbers in round 6+"

    def test_env_fallback_for_plugin_data(self):
        """Per C-H06: scripts use ${CLAUDE_PLUGIN_DATA:-/tmp} fallback"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "validate-no-numbers.sh")
        with open(path) as f:
            content = f.read()
        assert "CLAUDE_PLUGIN_DATA:-" in content, \
            "Must have fallback for CLAUDE_PLUGIN_DATA env var"


class TestCA5OathfishInit:
    """C-A.5: scripts/oathfish-init.sh -- Session start hook"""

    def test_file_exists(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "oathfish-init.sh")
        assert os.path.isfile(path)

    def test_is_executable(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "oathfish-init.sh")
        assert os.access(path, os.X_OK)

    def test_syntax_valid(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "oathfish-init.sh")
        result = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error: {result.stderr}"


class TestCA6ReinjectState:
    """C-A.6: scripts/oathfish-reinject-state.sh -- Compaction recovery"""

    def test_file_exists(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "oathfish-reinject-state.sh")
        assert os.path.isfile(path)

    def test_is_executable(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "oathfish-reinject-state.sh")
        assert os.access(path, os.X_OK)

    def test_syntax_valid(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "oathfish-reinject-state.sh")
        result = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_provides_recovery_instructions(self):
        """Script should output MCP recovery commands after compaction"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "oathfish-reinject-state.sh")
        with open(path) as f:
            content = f.read()
        assert "state_get" in content, \
            "Recovery script must mention state_get() for state recovery"


class TestCE1GetState:
    """C-E.1: scripts/get-state.sh -- Dynamic context injection"""

    def test_file_exists(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "get-state.sh")
        assert os.path.isfile(path)

    def test_is_executable(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "get-state.sh")
        assert os.access(path, os.X_OK)

    def test_syntax_valid(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "get-state.sh")
        result = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error: {result.stderr}"


class TestCE2Setup:
    """C-E.2: scripts/setup.sh -- Plugin setup"""

    def test_file_exists(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "setup.sh")
        assert os.path.isfile(path)

    def test_is_executable(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "setup.sh")
        assert os.access(path, os.X_OK)

    def test_syntax_valid(self):
        path = os.path.join(PLUGIN_ROOT, "scripts", "setup.sh")
        result = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_installs_requirements(self):
        """Setup must install Python dependencies"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "setup.sh")
        with open(path) as f:
            content = f.read()
        assert "pip" in content or "pip3" in content, \
            "Setup must install Python deps via pip"

    def test_verifies_mcp_server(self):
        """Setup must verify MCP server starts"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "setup.sh")
        with open(path) as f:
            content = f.read()
        assert "server" in content.lower(), \
            "Setup must verify MCP server"

    def test_creates_data_directory(self):
        """Setup must create data directory"""
        path = os.path.join(PLUGIN_ROOT, "scripts", "setup.sh")
        with open(path) as f:
            content = f.read()
        assert "mkdir" in content, "Setup must create data directory"
