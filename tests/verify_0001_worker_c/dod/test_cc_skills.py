"""
Verify Worker C Tasks C-C.1 through C-C.7: Skill definitions.
Tests verify Claude Code compliance per skills.md reference.
"""
import os
import re
import pytest

PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SKILLS_DIR = os.path.join(PLUGIN_ROOT, "skills")


def parse_frontmatter(filepath):
    """Parse YAML frontmatter from a markdown file."""
    with open(filepath) as f:
        content = f.read()
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return None, content
    import yaml
    fm = yaml.safe_load(match.group(1))
    body = content[match.end():]
    return fm, body


def count_lines(filepath):
    """Count lines in a file."""
    with open(filepath) as f:
        return sum(1 for _ in f)


class TestCC1OathfishDispatcher:
    """C-C.1: skills/oathfish/SKILL.md -- Dispatcher (inline)"""

    @pytest.fixture
    def skill_path(self):
        return os.path.join(SKILLS_DIR, "oathfish", "SKILL.md")

    @pytest.fixture
    def parsed(self, skill_path):
        return parse_frontmatter(skill_path)

    def test_file_exists(self, skill_path):
        assert os.path.isfile(skill_path)

    def test_has_frontmatter(self, parsed):
        fm, _ = parsed
        assert fm is not None

    def test_has_name(self, parsed):
        fm, _ = parsed
        assert fm.get("name") == "oathfish"

    def test_has_description(self, parsed):
        fm, _ = parsed
        assert "description" in fm

    def test_no_context_fork(self, parsed):
        """CRITICAL: Dispatcher must run INLINE (no context:fork)"""
        fm, _ = parsed
        assert fm.get("context") != "fork", \
            "oathfish dispatcher must run INLINE (no context:fork)"

    def test_has_argument_hint(self, parsed):
        fm, _ = parsed
        assert "argument-hint" in fm

    def test_under_500_lines(self, skill_path):
        """skills.md recommends keeping SKILL.md under 500 lines"""
        lines = count_lines(skill_path)
        assert lines < 500, f"Skill has {lines} lines, exceeds 500 limit"

    def test_uses_dynamic_context_injection(self, skill_path):
        """Spec: uses !`command` syntax for dynamic context"""
        with open(skill_path) as f:
            content = f.read()
        assert "!`" in content, \
            "Dispatcher should use dynamic context injection (!`command`)"

    def test_references_get_state_script(self, skill_path):
        with open(skill_path) as f:
            content = f.read()
        assert "get-state" in content, \
            "Dispatcher should reference get-state.sh for current state"

    def test_has_phase_sequence(self, skill_path):
        """Spec: C-07 phase sequence documented"""
        with open(skill_path) as f:
            content = f.read()
        for phase in ["UNDERSTAND", "BASELINE_AMPLIFY", "DELIBERATE",
                       "AMPLIFY", "SYNTHESIZE", "INTERACT", "COMPLETE"]:
            assert phase in content, f"Missing phase {phase} in dispatcher"

    def test_uses_arguments_substitution(self, skill_path):
        """skills.md: $ARGUMENTS used for topic input"""
        with open(skill_path) as f:
            content = f.read()
        assert "$ARGUMENTS" in content


class TestCC2Understand:
    """C-C.2: skills/understand/SKILL.md -- context:fork"""

    @pytest.fixture
    def skill_path(self):
        return os.path.join(SKILLS_DIR, "understand", "SKILL.md")

    @pytest.fixture
    def parsed(self, skill_path):
        return parse_frontmatter(skill_path)

    def test_file_exists(self, skill_path):
        assert os.path.isfile(skill_path)

    def test_has_context_fork(self, parsed):
        """Spec: understand runs with context:fork"""
        fm, _ = parsed
        assert fm.get("context") == "fork", \
            "understand skill must have context:fork"

    def test_is_not_user_invocable(self, parsed):
        """Internal skill -- not user-invocable"""
        fm, _ = parsed
        assert fm.get("user-invocable") is False, \
            "understand skill should not be user-invocable"

    def test_under_500_lines(self, skill_path):
        lines = count_lines(skill_path)
        assert lines < 500

    def test_references_competence_classifier(self, skill_path):
        """Spec C-31: question competence classifier before UNDERSTAND"""
        with open(skill_path) as f:
            content = f.read()
        assert "competence" in content.lower() or "classify" in content.lower(), \
            "understand skill must reference competence classifier (C-31)"

    def test_mentions_30_archetypes(self, skill_path):
        with open(skill_path) as f:
            content = f.read()
        assert "30" in content, "Must reference 30 archetypes"

    def test_mentions_structural_archetypes(self, skill_path):
        """C-36: 4 structural archetypes in every run"""
        with open(skill_path) as f:
            content = f.read()
        for archetype in ["Historian", "Systems Thinker", "Contrarian", "Probabilist"]:
            assert archetype in content, \
                f"Missing structural archetype: {archetype} (C-36)"


class TestCC3BaselineAmplify:
    """C-C.3: skills/baseline-amplify/SKILL.md -- context:fork"""

    @pytest.fixture
    def skill_path(self):
        return os.path.join(SKILLS_DIR, "baseline-amplify", "SKILL.md")

    @pytest.fixture
    def parsed(self, skill_path):
        return parse_frontmatter(skill_path)

    def test_file_exists(self, skill_path):
        assert os.path.isfile(skill_path)

    def test_has_context_fork(self, parsed):
        fm, _ = parsed
        assert fm.get("context") == "fork"

    def test_is_not_user_invocable(self, parsed):
        fm, _ = parsed
        assert fm.get("user-invocable") is False

    def test_under_500_lines(self, skill_path):
        lines = count_lines(skill_path)
        assert lines < 500

    def test_mentions_baseline(self, skill_path):
        """C-26: baseline amplification before deliberation"""
        with open(skill_path) as f:
            content = f.read()
        assert "baseline" in content.lower()


class TestCC4Deliberate:
    """C-C.4: skills/deliberate/SKILL.md -- INLINE, NO fork. CRITICAL."""

    @pytest.fixture
    def skill_path(self):
        return os.path.join(SKILLS_DIR, "deliberate", "SKILL.md")

    @pytest.fixture
    def parsed(self, skill_path):
        return parse_frontmatter(skill_path)

    def test_file_exists(self, skill_path):
        assert os.path.isfile(skill_path)

    def test_no_context_fork(self, parsed):
        """CRITICAL: deliberate MUST run inline. context:fork would break subagent spawning.
        Per C-L02: subagents cannot spawn other subagents."""
        fm, _ = parsed
        assert fm.get("context") != "fork", \
            "CRITICAL: deliberate skill MUST NOT have context:fork. " \
            "It must run inline for main-thread subagent spawning."

    def test_context_field_absent(self, parsed):
        """context field should be absent entirely (inline by default)"""
        fm, _ = parsed
        assert "context" not in fm, \
            "deliberate skill should NOT have context field at all (inline by default)"

    def test_is_not_user_invocable(self, parsed):
        fm, _ = parsed
        assert fm.get("user-invocable") is False

    def test_under_500_lines(self, skill_path):
        lines = count_lines(skill_path)
        assert lines < 500

    def test_references_agent_tool(self, skill_path):
        """Must use Agent tool to spawn archetypes"""
        with open(skill_path) as f:
            content = f.read()
        assert "Agent" in content or "@archetype" in content, \
            "deliberate skill must reference Agent tool for archetype spawning"

    def test_has_c33_enforcement(self, skill_path):
        """C-33 enforcement in deliberate skill"""
        with open(skill_path) as f:
            content = f.read()
        assert "C-33" in content, "deliberate skill must reference C-33 enforcement"

    def test_has_round_schedule(self, skill_path):
        """Round schedule must match spec"""
        with open(skill_path) as f:
            content = f.read()
        for rt in ["FREE_FORM", "STRUCTURED_DEBATE", "SCENARIO_REACTION", "PREDICTION"]:
            assert rt in content, f"Missing round type: {rt}"

    def test_writes_current_round_file(self, skill_path):
        """Must write .current_round for hook bridge"""
        with open(skill_path) as f:
            content = f.read()
        assert ".current_round" in content, \
            "Must write .current_round file for PreToolUse hook"

    def test_generates_deliberation_digest(self, skill_path):
        """Spec: Generates deliberation digest for AMPLIFY phase"""
        with open(skill_path) as f:
            content = f.read()
        assert "digest" in content.lower(), \
            "Must generate deliberation digest for post-deliberation amplification"


class TestCC5Amplify:
    """C-C.5: skills/amplify/SKILL.md -- context:fork"""

    @pytest.fixture
    def skill_path(self):
        return os.path.join(SKILLS_DIR, "amplify", "SKILL.md")

    @pytest.fixture
    def parsed(self, skill_path):
        return parse_frontmatter(skill_path)

    def test_file_exists(self, skill_path):
        assert os.path.isfile(skill_path)

    def test_has_context_fork(self, parsed):
        fm, _ = parsed
        assert fm.get("context") == "fork"

    def test_is_not_user_invocable(self, parsed):
        fm, _ = parsed
        assert fm.get("user-invocable") is False

    def test_under_500_lines(self, skill_path):
        lines = count_lines(skill_path)
        assert lines < 500

    def test_references_deliberation_digest(self, skill_path):
        """Post-deliberation amplification uses digest context"""
        with open(skill_path) as f:
            content = f.read()
        assert "digest" in content.lower()


class TestCC6Synthesize:
    """C-C.6: skills/synthesize/SKILL.md -- context:fork"""

    @pytest.fixture
    def skill_path(self):
        return os.path.join(SKILLS_DIR, "synthesize", "SKILL.md")

    @pytest.fixture
    def parsed(self, skill_path):
        return parse_frontmatter(skill_path)

    def test_file_exists(self, skill_path):
        assert os.path.isfile(skill_path)

    def test_has_context_fork(self, parsed):
        fm, _ = parsed
        assert fm.get("context") == "fork"

    def test_is_not_user_invocable(self, parsed):
        fm, _ = parsed
        assert fm.get("user-invocable") is False

    def test_under_500_lines(self, skill_path):
        lines = count_lines(skill_path)
        assert lines < 500

    def test_verifies_5_outputs(self, skill_path):
        """Must verify all 5 report outputs"""
        with open(skill_path) as f:
            content = f.read()
        expected = ["report.md", "reasoning-chains.md", "statistics.md",
                    "calibration.md", "diversity-trajectory.md"]
        found = sum(1 for e in expected if e in content)
        assert found >= 5, \
            f"Must verify 5 outputs, found {found}"

    def test_spawns_report_analyst(self, skill_path):
        """Must spawn report-analyst agent"""
        with open(skill_path) as f:
            content = f.read()
        assert "report-analyst" in content


class TestCC7Interact:
    """C-C.7: skills/interact/SKILL.md -- inline for resume"""

    @pytest.fixture
    def skill_path(self):
        return os.path.join(SKILLS_DIR, "interact", "SKILL.md")

    @pytest.fixture
    def parsed(self, skill_path):
        return parse_frontmatter(skill_path)

    def test_file_exists(self, skill_path):
        assert os.path.isfile(skill_path)

    def test_no_context_fork(self, parsed):
        """Spec: interact runs inline for archetype resume"""
        fm, _ = parsed
        assert fm.get("context") != "fork", \
            "interact skill must run inline for archetype resume via Agent tool"

    def test_under_500_lines(self, skill_path):
        lines = count_lines(skill_path)
        assert lines < 500

    def test_has_message_routing(self, skill_path):
        """Must route to archetypes or report analyst"""
        with open(skill_path) as f:
            content = f.read()
        assert "archetype" in content.lower()
        assert "report" in content.lower() or "analyst" in content.lower()
