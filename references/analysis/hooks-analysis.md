# Hooks — OathFish Analysis

**Source**: https://code.claude.com/docs/en/hooks-guide
**Date fetched**: 2026-03-18

---

## Reading the document

The Claude Code Hooks system provides 21 lifecycle events, 4 hook types, and a structured decision-control protocol that enables deterministic enforcement of rules during agent execution. Hooks fire at specific points in Claude Code's lifecycle — before tool calls, after tool calls, at session boundaries, during compaction, on teammate idle, on task completion — and communicate through stdin JSON, stdout JSON/text, stderr error messages, and exit codes.

The 21 hook events, in lifecycle order:

1. **SessionStart** — session begins, resumes, clears, or compacts. Matcher: `startup|resume|clear|compact`. Can inject context via stdout, persist env vars via `CLAUDE_ENV_FILE`.
2. **InstructionsLoaded** — CLAUDE.md or rules file loaded. No matcher. Async, audit-only.
3. **UserPromptSubmit** — user submits prompt, before processing. No matcher. Can block prompt or inject `additionalContext`.
4. **PreToolUse** — before tool execution. Matcher: tool name regex (`Bash`, `Edit|Write`, `mcp__.*`, `SendMessage`). Can return `permissionDecision: allow|deny|ask`. Can modify tool input via `updatedInput`.
5. **PermissionRequest** — permission dialog about to appear. Matcher: tool name. Can return `behavior: allow|deny` with optional `updatedPermissions`. Does NOT fire in headless mode (`-p`).
6. **PostToolUse** — after tool succeeds. Matcher: tool name. Cannot undo, but can inject context.
7. **PostToolUseFailure** — after tool fails. Matcher: tool name. Can inject context.
8. **Notification** — Claude sends notification. Matcher: `permission_prompt|idle_prompt|auth_success|elicitation_dialog`.
9. **SubagentStart** — subagent spawns. Matcher: agent type. Can inject context into subagent.
10. **SubagentStop** — subagent finishes. Matcher: agent type. Can block (force continuation) via `decision: "block"`. Has `stop_hook_active` field.
11. **Stop** — Claude finishes responding. No matcher. Can block via exit 2 or `decision: "block"`. Must check `stop_hook_active` to prevent infinite loops.
12. **TeammateIdle** — agent team member about to go idle. No matcher. Exit 2 sends feedback and continues. JSON `continue: false` stops teammate entirely.
13. **TaskCompleted** — task being marked complete. No matcher. Exit 2 prevents completion with feedback. JSON `continue: false` stops teammate.
14. **ConfigChange** — settings or skills file changes. Matcher: `user_settings|project_settings|local_settings|policy_settings|skills`. Can block with `decision: "block"`.
15. **WorktreeCreate** — worktree being created. No matcher. Command hooks only. Must print absolute path to stdout.
16. **WorktreeRemove** — worktree being removed. No matcher. Cannot block.
17. **PreCompact** — before compaction. Matcher: `manual|auto`. Exit 2 prevents compaction.
18. **PostCompact** — after compaction. Matcher: `manual|auto`. No decision control.
19. **Elicitation** — MCP server requests user input. Matcher: MCP server name. Can respond programmatically.
20. **ElicitationResult** — user responds to elicitation. Matcher: MCP server name. Can modify response.
21. **SessionEnd** — session terminates. Matcher: `clear|logout|prompt_input_exit|bypass_permissions_disabled|other`. Cannot block. Default timeout 1.5s.

The 4 hook types:

- **command** — shell command, receives JSON on stdin, communicates via stdout/stderr/exit codes. Default timeout: 600s.
- **http** — POST to URL, receives JSON as request body, returns JSON in response. Supports `$ENV_VAR` interpolation in headers via `allowedEnvVars`. Default timeout: 30s.
- **prompt** — single-turn LLM evaluation. Returns `{ok: true/false, reason: "..."}`. Default timeout: 30s. Uses fast model by default.
- **agent** — multi-turn subagent with tool access (Read, Grep, Glob, etc.). Same `ok/reason` format. Default timeout: 60s. Up to 50 tool-use turns.

Exit code semantics: 0 = proceed (parse stdout as JSON or context), 2 = block (stderr becomes feedback), other = non-blocking error (logged in verbose mode).

Key structural details:
- Matching hooks run in **parallel**; identical handlers deduplicated by command string or URL.
- Hook locations: `~/.claude/settings.json` (user), `.claude/settings.json` (project), `.claude/settings.local.json` (local), managed policy, plugin `hooks/hooks.json`, skill/agent YAML frontmatter.
- Environment variables: `CLAUDE_PROJECT_DIR`, `CLAUDE_CODE_REMOTE`, `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_ENV_FILE` (SessionStart only).
- `disableAllHooks: true` in settings turns off all hooks (except managed hooks cannot be disabled from lower scopes).
- Prompt/agent hooks supported on: PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest, Stop, SubagentStop, TaskCompleted, UserPromptSubmit.
- Async hooks (`"async": true`) run in background on: InstructionsLoaded, Notification, ConfigChange, WorktreeRemove, SessionEnd, PreCompact, PostCompact, SubagentStart.

---

## What I learned

**1. PreToolUse is a surgical enforcement layer, not just a gate.**

PreToolUse does not merely allow/block. It can:
- Modify the tool's input before execution (`updatedInput`), silently rewriting arguments.
- Add context to Claude's reasoning (`additionalContext`), steering behavior without blocking.
- Return `permissionDecision: "ask"` to escalate ambiguous cases to the human, rather than making a binary choice.

This means C-33 enforcement does not have to be a blunt "block if numbers detected" filter. The hook could strip numbers from a SendMessage body and inject a correction message ("Numbers removed — exchange arguments only in rounds 1-5"), or it could escalate to the coordinator for judgment.

However, there is a critical limitation: `permissionDecision: "allow"` does NOT override deny rules. If enterprise managed settings have a deny rule matching SendMessage, the hook's allow decision is ignored. For OathFish as a plugin, this is unlikely to be an issue, but it means hooks cannot grant permissions that policy forbids.

**2. TeammateIdle and TaskCompleted are distinct deliberation gates.**

TeammateIdle fires when a team member is *about to go idle* — this is the "are you really done thinking?" checkpoint. TaskCompleted fires when a task is being *marked as complete* — this is the "does this deliverable meet the quality bar?" checkpoint. OathFish needs both:
- TeammateIdle on archetype agents: "Have you addressed the strongest counterargument? Have you stated your position clearly?" (deliberation quality)
- TaskCompleted on the coordinator: "Have all 30 archetypes submitted round 6 predictions? Is the diversity index above threshold?" (structural completeness)

Exit 2 on either sends stderr as feedback and forces the agent to continue working. JSON `continue: false` stops the teammate entirely (useful for aborting a misbehaving archetype).

**3. Stop hooks are dangerous in deliberation contexts.**

The `stop_hook_active` field exists because Stop hooks can create infinite loops: Claude stops -> hook says "not done" -> Claude works more -> Claude stops -> hook says "not done" -> forever. The documentation explicitly warns to check this field. For OathFish's multi-round deliberation, a Stop hook on the coordinator that enforces "all 6 rounds completed" MUST check `stop_hook_active` or risk a deadlock where the coordinator can never stop.

**4. SessionStart with `compact` matcher is the compaction-recovery mechanism.**

When Claude's context fills up and compaction fires, SessionStart fires again with `source: "compact"`. Hooks can re-inject critical state. For OathFish, this is essential: if the coordinator's context is compacted mid-deliberation, the hook must re-inject the current run state (run_id, current round, active archetypes, diversity trajectory) or the deliberation will lose coherence.

**5. Prompt and agent hooks enable LLM-as-judge enforcement.**

Instead of writing a regex-based `validate-no-numbers.sh` that tries to pattern-match numeric predictions (fragile — what about "seventy percent" or "roughly 0.8"?), a prompt-type hook could ask a fast model: "Does this message contain a numeric prediction, probability estimate, confidence score, or quantitative stance? The message should contain only qualitative arguments, reasoning, and concerns. Respond {ok: false, reason: '...'} if numbers are present."

This is more robust than regex for natural language. But it adds latency (LLM call per SendMessage) and cost. For 30 archetypes x 5 rounds x ~2 messages per round = ~300 hook invocations during deliberation. At Haiku costs, this is cheap; at Sonnet costs, it adds up.

**6. SubagentStart hooks can inject per-round instructions.**

When an archetype subagent is spawned, SubagentStart fires with `agent_type` matching the agent name. The hook can inject `additionalContext` into the subagent's context. This means the coordinator does not need to pass round-specific instructions via SendMessage alone — the hook can inject round type, round number, and behavioral rules (e.g., "This is round 3, STRUCTURED_DEBATE. You must challenge your opponent's strongest argument.") directly into the subagent's context at spawn time.

However, SubagentStart cannot block subagent creation. If an archetype should not be spawned (e.g., it has been disqualified for consistent acquiescence), the coordinator must handle that logic before dispatching the subagent.

**7. PermissionRequest hooks do NOT fire in headless mode.**

This is a critical limitation for OathFish's mass amplification layer, which uses `claude -p` (headless/non-interactive). Any permission-based enforcement in the amplification layer MUST use PreToolUse hooks instead. The documentation is explicit: "Use PreToolUse hooks for automated permission decisions."

**8. Hook output is JSON-only for structured control; stdout text is context injection.**

There is a clean split: if your hook prints plain text to stdout and exits 0, that text is added to Claude's context. If it prints JSON, Claude Code parses it for decision fields. You cannot do both. This means `validate-no-numbers.sh` must choose: either it blocks with exit 2 + stderr message, or it returns structured JSON with `permissionDecision: "deny"`. It cannot block AND inject context simultaneously (though `permissionDecisionReason` in the JSON serves as feedback to Claude).

**9. Hooks in skill/agent frontmatter are scoped to that component's lifetime.**

The archetype-agent definition in the feature request (section 4.2.2) includes hooks in YAML frontmatter. Per the documentation, these hooks are active "while the skill or agent is active." For a persistent subagent with `memory: project`, "active" means the entire subagent session. The PreToolUse hook on SendMessage fires every time the archetype uses SendMessage, for the duration of the subagent's life. This is exactly the right scope for C-33 enforcement — it is per-archetype, not global.

Additionally, for subagents, Stop hooks defined in frontmatter are "automatically converted to SubagentStop." This means if the archetype-agent definition includes a Stop hook for quality checking, it becomes a SubagentStop hook at runtime, which is the correct event for a subagent.

**10. HTTP hooks enable external deliberation monitoring.**

An HTTP hook on PostToolUse (matcher: `SendMessage`) could POST every archetype message to an external monitoring service that tracks argument evolution, diversity metrics, and acquiescence patterns in real time. This separates the monitoring concern from the MCP server entirely — the MCP server handles deterministic state mutations, while the HTTP hook streams data to an analytics dashboard.

---

## What maps to OathFish

### SessionStart hook: run resume detection (feature-request §4.5)

The feature request specifies a `SessionStart` hook via `hooks/hooks.json` that runs `oathfish-init.sh` to "detect active OathFish runs, offer resume." The hooks documentation confirms this is the correct pattern.

**Implementation detail**: The SessionStart hook receives `{source: "startup|resume|clear|compact", session_id, cwd}`. The script should:
1. Check `$CLAUDE_PROJECT_DIR/docs/runs/` for directories with `state.json` where `status != "COMPLETE"`.
2. If active runs exist, print a context message to stdout: "Active OathFish run detected: RUN_ID at phase DELIBERATE, round 3 of 6. Resume with /oathfish --resume RUN_ID."
3. Use `CLAUDE_ENV_FILE` to persist the active run ID as an environment variable for subsequent Bash tool calls.

For the `compact` matcher case: re-inject the current run's phase, round, and critical state so the coordinator does not lose deliberation context after compaction.

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/oathfish-init.sh"
          }
        ]
      },
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/oathfish-reinject-state.sh"
          }
        ]
      }
    ]
  }
}
```

### PreToolUse hook on SendMessage: C-33 enforcement (validate-no-numbers.sh)

The archetype-agent frontmatter defines a PreToolUse hook on SendMessage that runs `validate-no-numbers.sh`. This is the primary enforcement mechanism for C-33: "No numeric predictions shared between archetypes until final independent round."

**What the hook must do**: Parse the SendMessage `tool_input` (which contains the message body the archetype is about to send), check for numeric predictions, and either block (exit 2) or deny (JSON with `permissionDecision: "deny"`).

**What "numeric predictions" means**: Not just digits. The hook must catch:
- Explicit numbers: "I estimate 73% probability", "stance: 0.6", "confidence: 85%"
- Spelled-out numbers: "roughly seventy percent", "about three-quarters likelihood"
- Implicit quantification: "I'd put this at highly likely" (borderline — this is qualitative framing of a quantitative judgment)

**Two implementation approaches**:

*Approach A — Regex-based command hook (deterministic, fast, fragile)*:
```bash
#!/bin/bash
INPUT=$(cat)
ROUND=$(echo "$INPUT" | jq -r '.tool_input.round // empty')
if [ "$ROUND" -ge 6 ] 2>/dev/null; then exit 0; fi

MESSAGE=$(echo "$INPUT" | jq -r '.tool_input.message // .tool_input.content // empty')
if echo "$MESSAGE" | grep -qiE '(stance|confidence|probability|likelihood|percent|[0-9]+%|\b0\.[0-9]+\b|\b[1-9][0-9]?\.[0-9]+\b)'; then
  echo "BLOCKED by C-33: No numeric predictions in rounds 1-5. Exchange arguments only." >&2
  exit 2
fi
exit 0
```

*Approach B — Prompt-based hook (robust, slower, costs per invocation)*:
```json
{
  "type": "prompt",
  "prompt": "You are a constraint validator for a deliberation system. The following message is from an archetype agent participating in rounds 1-5 of deliberation, where ONLY qualitative arguments are allowed — no numeric predictions, probability estimates, confidence scores, or quantitative stances. Does this message violate the no-numbers rule? $ARGUMENTS"
}
```

**Recommendation**: Use a two-layer approach. Regex catches obvious violations instantly (exit 2, zero cost). For messages that pass the regex, optionally escalate to a prompt hook for semantic validation. The regex is the fast path; the LLM is the safety net.

**Critical nuance**: The hook runs in the archetype-agent's frontmatter scope, meaning it fires only for that specific subagent's SendMessage calls. It does NOT affect the coordinator's SendMessage calls (which legitimately contain round metadata, archetype assignments, etc.). This is the correct scoping — the constraint applies to archetypes sharing numeric predictions with each other, not to the coordinator communicating round structure.

**Round detection**: The hook needs to know the current round number to allow numbers in round 6. The `tool_input` for SendMessage may not contain round metadata. Options:
1. The coordinator includes round number in every message to archetypes; the archetype echoes it back.
2. The hook queries the MCP server for current round (adds latency, requires MCP access from a command hook — not directly possible; would need a file-based checkpoint).
3. Use `CLAUDE_ENV_FILE` at SubagentStart to set `OATHFISH_CURRENT_ROUND=N` as an environment variable.
4. The deliberation engine writes the round number to a known file path; the hook reads it.

Option 4 is the most robust for a command hook: `cat $CLAUDE_PROJECT_DIR/docs/runs/$RUN_ID/.current_round`.

### TeammateIdle: deliberation quality gates

TeammateIdle fires when an archetype team member is about to go idle. This is the natural enforcement point for:

- **Argument completeness**: "Did you address the strongest counterargument from the previous round?" (C-33 spirit: arguments must be substantive, not just token compliance)
- **Structured stubbornness**: "Did you push back on challenges to your domain expertise?" (2305.14325: stubborn prompts produce better outcomes)
- **Response format compliance**: "Does your response follow the expected argument structure for this round type?"

**Implementation**:
```json
{
  "hooks": {
    "TeammateIdle": [
      {
        "hooks": [
          {
            "type": "agent",
            "prompt": "Review this teammate's last message. Verify: (1) they addressed at least one counterargument from the previous round, (2) they stated their position clearly with supporting reasoning, (3) they did not include numeric predictions (rounds 1-5 only). If any check fails, respond with {ok: false, reason: 'specific feedback'}. $ARGUMENTS",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

The agent-type hook is appropriate here because it needs to read the teammate's last message (available in `last_assistant_message` for SubagentStop, but TeammateIdle provides `teammate_name` and `team_name` — the hook may need to access the transcript to evaluate quality).

### TaskCompleted: structural completeness gates

TaskCompleted fires when a task is being marked as complete. For OathFish, this maps to:

- **Deliberation completion**: "All 6 rounds completed, all 30 archetypes submitted predictions in round 6, diversity index above minimum threshold." If the coordinator tries to mark DELIBERATE as complete without these conditions, exit 2 forces continuation.
- **Amplification completion**: "All N amplification calls completed, results aggregated, debiasing applied." Prevents premature synthesis.
- **Synthesis completion**: "Report includes all required sections, calibration metrics computed, both raw and corrected Brier reported." Prevents incomplete deliverables.

**Implementation**:
```bash
#!/bin/bash
INPUT=$(cat)
TASK_SUBJECT=$(echo "$INPUT" | jq -r '.task_subject')
RUN_DIR="$CLAUDE_PROJECT_DIR/docs/runs/$(cat $CLAUDE_PROJECT_DIR/.active_run)"

case "$TASK_SUBJECT" in
  *DELIBERATE*)
    ROUND=$(jq -r '.current_round' "$RUN_DIR/state.json")
    PREDICTIONS=$(ls "$RUN_DIR/round_6_predictions/" 2>/dev/null | wc -l)
    if [ "$ROUND" -lt 6 ] || [ "$PREDICTIONS" -lt 30 ]; then
      echo "DELIBERATE incomplete: round=$ROUND, predictions=$PREDICTIONS/30" >&2
      exit 2
    fi
    ;;
esac
exit 0
```

### PostCompact (via SessionStart compact matcher): state re-injection

When compaction fires mid-deliberation, critical state is lost from the coordinator's context. The SessionStart hook with `compact` matcher re-injects:
- Current run ID, phase, round number
- Active archetype list and their last known positions (text summaries)
- Diversity trajectory so far
- Any pending tasks or round assignments

This is essential for C-16 (any phase resumable from checkpoint). Compaction is an implicit checkpoint that must not break deliberation continuity.

### SubagentStart: round-specific instruction injection

When an archetype subagent starts for a new round, the SubagentStart hook can inject round-specific context:
```json
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "archetype-.*",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/inject-round-context.sh"
          }
        ]
      }
    ]
  }
}
```

The script reads the current round type and number from the MCP state file and prints instructions to stdout, which are injected into the subagent's context. This supplements the coordinator's SendMessage with standardized round rules.

---

## What maps to the research

### 2402.19379 (Wisdom of the Silicon Crowd) — Acquiescence bias enforcement

The paper's central finding: 57% positive prediction rate (M=57.35, t(1006)=86.20, p<0.001) when LLMs see others' numeric predictions. Social updating degrades accuracy (GPT-4: p=0.011; Claude 2: p=0.001).

**Hook mapping**: The PreToolUse hook on SendMessage is the direct architectural response. By blocking numeric predictions in rounds 1-5 (C-33), the hook prevents the exact mechanism that causes acquiescence bias — archetypes seeing others' numbers and anchoring-and-adjusting toward them. The hook enforces what the paper empirically demonstrates: independent prediction aggregation beats social updating.

**Critical gap**: The paper also shows that simple averaging beats LLM-driven updating. OathFish's argument-only deliberation (rounds 1-5) is a novel middle ground not tested in the paper. The paper tested numeric updating; OathFish proposes qualitative argument exchange without numbers. This is genuinely new territory. The hooks enforce the "no numbers" half of the design, but cannot verify that qualitative argument exchange actually improves over no exchange at all. Only the A/B test infrastructure (C-26) can verify that.

### 2305.14325 (Multi-Agent Debate) — Stubbornness via quality gates

The paper finds that "more stubborn [prompts] led to LONGER debates and BETTER final solutions." Stubborn agents resist changing their position unless given compelling evidence.

**Hook mapping**: TeammateIdle hooks can enforce structured stubbornness. When an archetype is about to go idle after a round, the hook checks: "Did you maintain your domain expertise position, or did you capitulate to social pressure?" If the archetype abandoned its core position without addressing a compelling counterargument, the hook sends feedback: "You changed your position without addressing the counterargument about [X]. Reconsider."

This is not deterministic stubbornness (which would be brittle) — it is LLM-evaluated stubbornness (via a prompt or agent hook), which can distinguish between genuine persuasion and acquiescence. The agent-type hook can read the previous round's arguments to verify whether the archetype's position change was evidence-driven.

The paper also warns about confident false consensus. A Stop hook on the coordinator can check: "Is the diversity index above threshold? If all archetypes converged to the same position before round 6, this may be false consensus — investigate before stopping." (C-32)

### 2409.19839 (ForecastBench) — Competence boundary detection

The paper shows superforecasters significantly outperform LLMs (p<0.001) and that LLMs lack competence boundary detection — they produce confident noise on out-of-domain questions.

**Hook mapping**: A UserPromptSubmit hook could classify incoming questions before the OathFish pipeline begins. If the question is outside the archetype set's domain competence (per C-31), the hook injects a warning: "This question may be outside the current archetype set's expertise. Consider: (a) proceeding with reduced confidence, (b) generating domain-specific archetypes, or (c) routing directly to amplification without deliberation."

This is a lightweight implementation of C-31 that does not require a separate classifier service — the hook IS the classifier, implemented as a prompt-type hook that evaluates the question against known archetype domains.

### 2411.10109 (Generative Agent Simulations of 1,000 People) — Grounding verification

The paper demonstrates 85% fidelity with real interview data, establishing that synthetic agents CAN replicate human behavior when grounded in real data.

**Hook mapping**: A PreToolUse hook on the archetype creation tool (during UNDERSTAND phase) could verify that each archetype definition includes the required 3-5 real public sources (C-29). If the coordinator creates an archetype without grounding sources, the hook blocks with: "Archetype lacks grounding sources. C-29 requires 3-5 curated real public sources per archetype before production."

This is enforcement-at-creation, not enforcement-at-runtime. The hook catches ungrounded archetypes before they participate in deliberation, rather than trying to detect ungrounded reasoning after the fact.

### 2602.19520 (Calibration Decomposition) — Debiasing trigger hooks

The paper establishes that domain-level bias is detectable at n=90 (80% power at d=0.3) and that 87.3% of calibration variance is explained by 4 decomposable components.

**Hook mapping**: A PostCompact or SessionStart hook could check the calibration database for domain-level bias corrections at the start of each run. If corrections are available (run >= 3, n >= 90/domain per C-27), the hook injects them into the coordinator's context: "Domain-level acquiescence corrections available: Technology +3.2%, Healthcare -1.8%, Finance +5.1%. Apply during amplification aggregation."

This ensures debiasing is not forgotten or skipped — the hook deterministically reminds the coordinator to apply corrections when they are statistically justified.

---

## What 10x the outcome

### 1. Prompt-hook cascade for C-33 enforcement

Replace the single `validate-no-numbers.sh` with a three-tier enforcement cascade:

**Tier 1** (command hook, ~0ms): Regex scan for obvious numeric patterns (`\d+%`, `0.\d+`, `stance:`, `confidence:`). Catches 80% of violations instantly. Exit 2 on match.

**Tier 2** (prompt hook, ~500ms): For messages that pass Tier 1, a fast-model prompt evaluates: "Does this contain quantitative predictions, probability estimates, or numeric stances expressed in words?" Catches "roughly seventy percent" and "highly likely (above 90%)". Returns `{ok: false}` on violation.

**Tier 3** (agent hook, ~5s, sampled): For every 10th message (or randomly), an agent hook spawns a verifier that reads the archetype's full conversation history and checks for *implicit* numeric anchoring — cases where an archetype references another archetype's position in a way that implies they know the numeric stance. This catches social information leakage that no single-message filter can detect.

The cascade balances speed (Tier 1 handles most cases instantly) with robustness (Tier 3 catches subtle violations that would otherwise erode C-33's protection against acquiescence bias). The tiered approach avoids paying LLM costs on every message while still providing deep enforcement where it matters.

### 2. Diversity-preserving deliberation via Stop + TeammateIdle hooks

Rather than monitoring diversity index passively (via MCP tools called by the coordinator), enforce it actively via hooks:

**Stop hook on coordinator**: Before the coordinator can end a deliberation round, check the diversity index. If diversity dropped below 0.15 since the previous round (premature consensus per C-32), inject: "PREMATURE CONSENSUS DETECTED. Diversity index fell from X to Y. Before proceeding, inject a contrarian perspective or revisit the most-abandoned minority position."

**TeammateIdle hook on archetypes**: When an archetype goes idle, check whether its position is within 0.1 standard deviations of the group mean (based on text similarity of argument themes, not numeric stances). If so, send feedback: "Your position is indistinguishable from the group consensus. You represent the {segment} perspective — what would a real {segment} stakeholder push back on that the group is accepting too easily?"

This creates a diversity-preserving feedback loop where hooks actively resist the natural tendency of LLM agents to converge, which is the core architectural lesson from 2305.14325 (stubborn = better) and 2402.19379 (independent > social).

### 3. A/B test enforcement via TaskCompleted hooks

C-26 requires baseline amplification BEFORE deliberation every run. This is the most important scientific control in the system (spec-audit SPEC-02). A TaskCompleted hook on the UNDERSTAND phase can enforce this:

```bash
# When UNDERSTAND is marked complete, check that baseline exists
if [ ! -f "$RUN_DIR/baseline_amplification_results.json" ]; then
  echo "BLOCKED: C-26 requires baseline amplification before deliberation. Run baseline amplification first." >&2
  exit 2
fi
```

The coordinator cannot proceed to DELIBERATE until baseline amplification is recorded. This is deterministic enforcement of the A/B test protocol — no amount of LLM reasoning can skip this step.

### 4. Real-time deliberation analytics via HTTP hooks

PostToolUse HTTP hooks on SendMessage could stream every archetype message to an external analytics service that computes:
- Real-time argument evolution graphs
- Influence chains (which archetypes are citing which)
- Diversity trajectory visualization
- Acquiescence detection (which archetypes are capitulating most frequently)

This separates analytics from the MCP server (which handles deterministic state) and from the agents (which handle reasoning). The HTTP hook is fire-and-forget (async), adding zero latency to deliberation while enabling a live monitoring dashboard.

### 5. Compaction-resilient deliberation via PreCompact + PostCompact hooks

Compaction during a 6-round deliberation with 30 archetypes is almost inevitable — the context window will fill. The PreCompact hook can:
1. Snapshot the full deliberation state to disk (run ID, round, all positions, diversity trajectory) — this is a deterministic save, not relying on the LLM's compaction summary.
2. The PostCompact hook verifies the compaction summary includes critical deliberation context and injects corrections if not.
3. The SessionStart `compact` hook re-injects the full state snapshot on compaction recovery.

This three-hook pattern (PreCompact save, PostCompact verify, SessionStart restore) makes deliberation compaction-proof. Without it, a compaction mid-round could lose archetype positions, round context, and diversity trajectory — corrupting the entire run.

### 6. Archetype behavioral drift detection via SubagentStop hooks

Over multiple rounds, archetypes may drift from their defined persona. A SubagentStop hook (using agent type) can verify persona consistency:

```json
{
  "type": "agent",
  "prompt": "Compare this archetype's final message with its persona definition. Is the archetype still reasoning from its defined segment perspective, or has it drifted toward generic LLM reasoning? Check for: (1) domain-specific vocabulary, (2) segment-specific concerns, (3) values alignment with persona definition. $ARGUMENTS"
}
```

This catches a failure mode unique to multi-round deliberation: after 5 rounds of debate, archetypes may converge not just in position but in *reasoning style*, losing the diversity that makes the ensemble valuable (WARNING-07: single-model correlated failures).

---

## Why?

The hooks system is the enforcement layer that converts OathFish's research-grounded design constraints from "instructions the LLM should follow" into "rules the system deterministically enforces." This distinction is existential for the project.

**Without hooks**, C-33 is a prompt instruction: "Do not share numeric predictions in rounds 1-5." LLMs follow instructions most of the time, but acquiescence bias (2402.19379) means archetypes will sometimes include numbers anyway — especially when they see other archetypes' arguments that imply quantitative positions. A single leaked number in round 3 can anchor 29 other archetypes for the remaining rounds, destroying the independence that makes ensemble prediction work. The probability of zero leakage across 30 archetypes x 5 rounds x ~2 messages = 300 messages is low. Even a 99% per-message compliance rate yields ~3 leaked numeric predictions per deliberation.

**With hooks**, C-33 is a deterministic gate: no message containing numeric predictions passes through SendMessage in rounds 1-5, period. The system does not rely on LLM compliance. It enforces compliance. This is the difference between "we hope the agents follow the rules" and "the rules are physically enforced." For a system whose entire predictive value depends on independent prediction aggregation (the core finding of 2402.19379), this enforcement is not optional.

The same logic applies to every constraint that hooks enforce:
- C-26 (baseline before deliberation) — without hooks, the coordinator might skip baseline "to save time." With TaskCompleted hooks, it literally cannot.
- C-32 (diversity monitoring) — without hooks, premature consensus goes undetected until the report is generated. With Stop hooks, the coordinator is forced to address diversity collapse in real time.
- C-16 (resumability) — without hooks, compaction can destroy deliberation state. With PreCompact/PostCompact/SessionStart hooks, the state is preserved deterministically.

The research is clear: LLM agents left to self-govern will converge, acquiesce, and produce confidently wrong consensus (2305.14325, 2402.19379). Hooks are the architectural immune system that prevents these failure modes.

---

## Reality check?

### What hooks CANNOT do

**1. Hooks cannot enforce reasoning quality, only structural compliance.**

A PreToolUse hook can block numeric predictions in SendMessage. It cannot ensure that the qualitative arguments being exchanged are *good* arguments. An archetype that sends "I agree with everything" with no numbers passes C-33 but violates the spirit of deliberation. Prompt-type and agent-type hooks can partially address this (by evaluating argument quality), but they introduce LLM judgment into the enforcement layer — which means they are probabilistically correct, not deterministically correct. The "immune system" metaphor breaks down for quality checks.

**2. Hooks add latency to every enforced tool call.**

Every PreToolUse hook on SendMessage adds latency before the message is sent. For a command hook running a bash script with `jq` parsing: ~50-100ms. For a prompt hook with an LLM call: ~500-2000ms. For an agent hook: ~5-30s. With 300 SendMessage calls during deliberation, a prompt-hook cascade adds 2.5-10 minutes of total enforcement overhead. This is acceptable for a system that runs for hours, but it should be measured and reported.

**3. Hooks run in parallel but decisions are merged, not sequenced.**

If two hooks fire on the same PreToolUse event and one returns `allow` while the other returns `deny`, the deny wins (most restrictive wins). This is correct for OathFish, but it means hook interactions must be designed carefully. A hook that allows SendMessage for round 6 predictions must not conflict with a hook that blocks all SendMessage calls that contain numbers. The round-detection logic must be consistent across all hooks on SendMessage.

**4. PermissionRequest hooks do not fire in headless mode (`-p`).**

OathFish's mass amplification layer uses `claude -p`. Any enforcement needed during amplification (e.g., validating that amplification prompts include the deliberation digest per SPEC-03 resolution) must use PreToolUse hooks, not PermissionRequest hooks. This is a documentation constraint that is easy to miss.

**5. The `validate-no-numbers.sh` script must handle the round 6 exception.**

The biggest implementation risk for C-33 enforcement is the round 6 exception. In round 6 (INDEPENDENT_PREDICTION), archetypes MUST include numeric predictions — that is the whole point. The hook must reliably distinguish round 6 from rounds 1-5. If it blocks round 6 predictions, the deliberation cannot produce output. If it allows round 5 predictions (misidentifying them as round 6), it defeats C-33.

The round number is not in the default SendMessage tool_input schema. It must be available through one of: (a) a file written by the MCP state machine, (b) an environment variable set by SubagentStart, (c) metadata in the SendMessage body, (d) the hook querying the MCP server. Option (a) is most reliable for a command hook. Option (b) requires CLAUDE_ENV_FILE. Options (c) and (d) add complexity and fragility.

**6. Stop hook infinite loops are a real risk for deliberation.**

OathFish's deliberation coordinator naturally stops after each round to wait for archetype responses. If a Stop hook on the coordinator checks "are all rounds complete?" and the answer is "no" (because only round 1 is done), it will force the coordinator to continue — but the coordinator may not know what to do next without the round results. This creates a confused state where the coordinator is forced to keep working but has nothing actionable. The hook must distinguish "stopped after dispatching round N" (expected, should not block) from "stopped before completing all 6 rounds" (unexpected, should block).

**7. Hook timeout defaults may be too aggressive for agent hooks.**

Agent hooks default to 60 seconds. An agent hook that verifies deliberation quality by reading multiple archetype messages and checking argument completeness may need longer. The `timeout` field can be set per hook, but if unset, a complex quality verification could timeout and silently fail (non-blocking error logged in verbose mode only). All agent hooks in OathFish should explicitly set timeouts appropriate to their verification scope.

**8. Single-model limitation applies to prompt/agent hooks too.**

Prompt and agent hooks use Claude models to evaluate conditions. These models share the same training data, RLHF objectives, and reasoning patterns as the archetypes they are evaluating (WARNING-07). A prompt hook that checks for acquiescence bias is itself subject to the same biases. An agent hook that evaluates argument quality may share the same blind spots as the archetype it is reviewing. This is a fundamental limitation: the enforcement layer has correlated failures with the system it enforces.

Mitigation: use the fastest/cheapest model for enforcement hooks (Haiku) while using deeper models (Opus/Sonnet) for archetypes. Different model sizes have somewhat different error profiles, providing partial decorrelation.

---

## Citations from the references document

### Hook events cited

| Hook Event | OathFish Use | Constraint | Source |
|---|---|---|---|
| SessionStart (startup) | Detect active runs, offer resume | C-16 (resumability) | feature-request §4.5; hooks-guide SessionStart |
| SessionStart (compact) | Re-inject deliberation state after compaction | C-16, C-15 (persistence) | hooks-guide §Re-inject context after compaction |
| PreToolUse (SendMessage) | Block numeric predictions rounds 1-5 | C-33 (no numbers until round 6) | feature-request §4.2.2 archetype-agent frontmatter; hooks-guide §PreToolUse |
| TeammateIdle | Enforce argument completeness, structured stubbornness | C-33 spirit, C-32 (diversity) | hooks-reference TeammateIdle; 2305.14325 (stubborn = better) |
| TaskCompleted | Enforce structural completeness per phase | C-26 (baseline before deliberation), C-07 (state machine) | hooks-reference TaskCompleted |
| Stop | Diversity index check before coordinator proceeds | C-32 (premature consensus = failure) | hooks-guide §Stop; hooks-reference stop_hook_active |
| SubagentStart | Inject round-specific instructions into archetypes | C-10 (round types), C-30 (superforecaster methodology) | hooks-reference SubagentStart additionalContext |
| SubagentStop | Persona drift detection | WARNING-07 (single-model correlation) | hooks-reference SubagentStop |
| PostToolUse (SendMessage) | Stream messages to analytics | Monitoring, not constraint | hooks-guide §PostToolUse; hooks-reference HTTP hooks |
| PreCompact | Snapshot deliberation state before compaction | C-15 (persistence), C-16 (resumability) | hooks-reference PreCompact |
| PostCompact | Verify compaction summary integrity | C-16 (resumability) | hooks-reference PostCompact |
| UserPromptSubmit | Question competence classification | C-31 (competence classifier) | hooks-reference UserPromptSubmit additionalContext |
| PermissionRequest | Not used — does not fire in headless mode | N/A for amplification layer | hooks-guide §Limitations |

### Constraints cited

| C-ID | Constraint | Hook Enforcement | Research Basis |
|---|---|---|---|
| C-33 | No numeric predictions shared until final round | PreToolUse on SendMessage (archetype frontmatter) | 2402.19379 (acquiescence 57%, p<0.001; social updating degrades accuracy p=0.011) |
| C-32 | Diversity index tracked per round; premature consensus triggers contrarian | Stop hook on coordinator | 2305.14325 (convergence = false consensus; stubborn = better outcomes) |
| C-26 | Baseline amplification BEFORE deliberation every run | TaskCompleted hook on UNDERSTAND phase | 2402.19379 (simple averaging beats LLM updating); final-synthesis Tier 2 #5 |
| C-16 | Any phase resumable from checkpoint | SessionStart (startup + compact), PreCompact, PostCompact | feature-request §6.2 |
| C-15 | Disk persistence after every mutation | PreCompact (snapshot before compaction) | feature-request §6.2 |
| C-14 | Argument evolution tracked rounds 1-5; numeric only round 6 | PreToolUse validates format per round type | AMB-01 in spec-audit; 2305.14325 + 2402.19379 |
| C-07 | 5-phase state machine | TaskCompleted validates phase completion criteria | feature-request §6.1 |
| C-10 | 4 round types + INDEPENDENT_PREDICTION | SubagentStart injects round-type-specific rules | feature-request §6.1; research-driven-redesign §2.1 |
| C-27 | Per-domain acquiescence tracking from run 1 | SessionStart injects available corrections at run start | 2402.19379 (acquiescence); 2602.19520 (domain-level bias at n=90) |
| C-30 | Superforecaster methodology in every archetype | SubagentStart injects methodology reminder | 2409.19839 (superforecasters beat LLMs p<0.001) |
| C-31 | Question competence classifier before UNDERSTAND | UserPromptSubmit prompt hook for classification | 2409.19839 (no competence boundary detection) |
| C-29 | Ground archetypes in 3-5 real public sources | PreToolUse on archetype creation tool | 2411.10109 (85% fidelity with real data) |

### Research papers cited

| Paper ID | Key Finding for Hooks | Hook Mapping |
|---|---|---|
| 2402.19379 | 57% acquiescence rate (p<0.001); social updating degrades accuracy (p=0.011 GPT-4, p=0.001 Claude 2); simple averaging beats updating | PreToolUse on SendMessage blocks numeric sharing (C-33); eliminates the mechanism that causes acquiescence |
| 2305.14325 | Stubborn prompts produce longer debates and better outcomes; convergence into single answers not necessarily correct | TeammateIdle enforces stubbornness; Stop hook detects premature consensus; agent hooks verify argument quality |
| 2409.19839 | Superforecasters significantly outperform LLMs (p<0.001); LLMs lack competence boundary detection | UserPromptSubmit prompt hook for competence classification (C-31); SubagentStart injects superforecaster methodology (C-30) |
| 2411.10109 | 85% fidelity with real interview data; grounding in real data produces step-function improvement | PreToolUse on archetype creation verifies grounding sources (C-29) |
| 2602.19520 | 87.3% calibration variance explained by 4 components; domain-level bias detectable at n=90 (80% power at d=0.3) | SessionStart injects domain-level bias corrections when available (C-27); TaskCompleted verifies debiasing applied in amplification |

### Spec audit issues cited

| Issue ID | Description | Hook Relevance |
|---|---|---|
| SPEC-01 | Position model assumes numbers every round; C-33/C-14 forbid until round 6 | PreToolUse hook is the enforcement mechanism that makes C-33 operational despite the data model conflict |
| SPEC-02 | Baseline must run before deliberation; state machine forbids AMPLIFY before DELIBERATE | TaskCompleted hook on UNDERSTAND ensures baseline runs before DELIBERATE begins |
| AMB-01 | Evolution tracking requires numeric stances that do not exist in rounds 1-5 | Hooks enforce the no-numbers rule; evolution tracking must be redesigned to work with qualitative data (not a hook concern, but hooks make the constraint real) |
| WARNING-07 | Single-model correlated failures; effective ensemble size may be 3-5, not 30 | SubagentStop agent hooks can detect persona drift toward generic reasoning; prompt hooks share this limitation (same model family) |
