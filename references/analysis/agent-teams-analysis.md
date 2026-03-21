# Agent Teams — OathFish Analysis

**Source**: https://code.claude.com/docs/en/agent-teams
**Date fetched**: 2026-03-18

---

## <reading document>

The Agent Teams documentation describes an **experimental** feature (requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) that enables multiple Claude Code instances to work together. The architecture is: one **team lead** (the main session), N **teammates** (separate Claude Code instances), a **shared task list** (pending/in-progress/completed with dependencies and file-locked claiming), and a **mailbox** (SendMessage to one, Broadcast to all).

Key mechanics I noted on close reading:

1. **Teammates are full Claude Code sessions.** Each has its own context window, loads CLAUDE.md and MCP servers independently, but does NOT inherit the lead's conversation history. They receive only the spawn prompt.

2. **Communication is real-time.** Messages are delivered automatically -- no polling. Idle notifications are auto-sent to lead. This is critical: OathFish's debate rounds require back-and-forth exchange, and the messaging system supports it natively.

3. **Task system is coordination-oriented, not conversation-oriented.** Tasks have three states, support dependencies, and use file locking for claim arbitration. This is designed for parallel work items (implement module A, review module B), not for multi-round dialogue.

4. **Plan approval exists.** Teammates can work in read-only plan mode until the lead approves. This maps to OathFish's coordinator-approval pattern, but the approval is binary (approve/reject), not structured.

5. **Hooks are the enforcement mechanism.** `TeammateIdle` (exit 2 = keep working) and `TaskCompleted` (exit 2 = prevent completion) are the only programmatic control points. Everything else is natural-language instruction to the lead.

6. **No hard limit on teammate count is stated.** The docs say "There's no hard limit on the number of teammates, but practical constraints apply" -- then recommend 3-5. The practical constraints are: token cost scales linearly, coordination overhead increases, diminishing returns.

7. **No nested teams.** Teammates cannot spawn their own teams. Only the lead manages the team.

8. **No session resumption for in-process teammates.** `/resume` and `/rewind` do not restore teammates. After resuming, the lead may try to message teammates that no longer exist.

9. **One team per session.** Must clean up before starting a new one.

10. **Permissions propagate from lead.** All teammates start with lead's permissions. Can change individually after spawning, but not at spawn time.

---

## <what I learned>

The fundamental thing I learned is that **Agent Teams is a coordination layer for parallel independent work, not a debate infrastructure**. Every example in the docs -- code review, feature implementation, debugging hypotheses -- involves teammates working independently on separate concerns and reporting findings. The "competing hypotheses" example is the closest to OathFish's debate pattern, but even there, the teammates investigate independently and then challenge each other's findings. They do not engage in structured multi-round deliberation with a coordinator orchestrating turn-by-turn exchanges.

Specific revelations:

**No hard teammate cap, but severe soft limits.** The docs never say "maximum 30" or "maximum 32." They say "no hard limit" but recommend 3-5. C-18 in OathFish's spec states "Claude Teams ~30 concurrent agents maximum" as a LIMITATION -- but this constraint appears to be self-imposed by the OathFish spec authors, not documented by Anthropic. The actual limitation is economic and practical: each teammate is a separate Claude Code instance with its own context window. At 30 teammates, you are running 30 concurrent Opus/Sonnet sessions plus the lead. The token cost alone is staggering.

**The task system does not model deliberation rounds.** Tasks are work items to be completed (pending -> in-progress -> completed). OathFish's deliberation rounds are NOT tasks in this sense -- they are phases of a conversation where archetypes exchange arguments. Mapping "Round 1: FREE_FORM argument exchange" to a task that 30 archetypes claim and complete is a category error. The task system is for dividing work, not orchestrating dialogue.

**SendMessage is the right primitive, but the throughput is unknown.** The docs confirm one-to-one messaging and broadcast. OathFish needs the coordinator to send structured prompts to all 30 archetypes per round (broadcast), collect their responses, process them, and send the next round's prompts. This is 6 rounds x 30 messages minimum = 180+ SendMessage operations just for the basic flow, plus debate exchanges in rounds 3-4 where paired archetypes go back and forth. The docs provide zero information about message throughput, latency, or ordering guarantees.

**Subagents are fundamentally different from teammates.** The docs explicitly contrast: subagents report results back to the caller and never talk to each other. Teammates share a task list, claim work, and communicate directly. OathFish needs archetypes to communicate with each other (via coordinator-mediated SendMessage) -- this maps to Teams, not subagents. But the v3 redesign proposes making archetypes persistent subagents instead of Team members. This creates a contradiction: subagents CANNOT communicate with each other. If archetypes are subagents, they can only report back to the coordinator, not debate.

**The "competing hypotheses" example validates OathFish's concept but at 5 agents, not 30.** The docs' example spawns 5 agents to investigate different theories and "talk to each other to try to disprove each other's theories, like a scientific debate." This is exactly OathFish's deliberation model -- but at 1/6th the scale.

---

## <what maps to OathFish>

### Direct mappings (confirmed by docs)

| OathFish Concept | Agent Teams Feature | Mapping Quality |
|------------------|-------------------|-----------------|
| TeamCreate("oathfish-{RUN_ID}") | Team lead creates team | DIRECT -- team lead spawns teammates |
| Coordinator orchestrates rounds | Lead assigns tasks, synthesizes | PARTIAL -- lead coordinates, but via tasks not dialogue rounds |
| SendMessage for debate exchanges | SendMessage (one-to-one) | DIRECT -- but OathFish needs coordinator-mediated relay, not peer-to-peer |
| Broadcast for round prompts | Broadcast (to all) | DIRECT -- but "use sparingly, costs scale with team size" at 30 = expensive |
| 30 archetype agents | Teammates | FEASIBLE but 6x beyond recommended range |
| Task dependencies | Task system with dependencies | PARTIAL -- round ordering maps to task dependencies, but rounds are not tasks |
| TeammateIdle hook | TeammateIdle (exit 2 = keep working) | DIRECT -- can force archetypes to continue deliberating |
| Plan approval for reasoning | Plan mode until lead approves | PARTIAL -- binary approve/reject, not structured argument review |
| Config at ~/.claude/teams/ | config.json with members array | DIRECT |

### Mappings that break down

| OathFish Assumption | Reality from Docs | Gap |
|---------------------|-------------------|-----|
| Archetypes engage in structured multi-round debate | Teams designed for parallel independent work | Teams has messaging, but no debate orchestration primitive |
| Coordinator manages turn-by-turn dialogue | Lead manages tasks and synthesis | Lead can SendMessage, but managing 30 simultaneous dialogues across 6 rounds requires extraordinary prompt engineering |
| 30 agents communicating simultaneously | Recommended 3-5 teammates | 6-10x beyond recommended. "Diminishing returns beyond a certain point" |
| Persistent archetype identity across rounds | Teammates load CLAUDE.md + spawn prompt only | No conversation history inheritance. Each teammate starts fresh with spawn prompt only. Memory:project is for subagents, not teammates. |
| Arguments-only rounds then independent prediction | No structured round management | All round structuring must be done via natural language instructions to lead and archetypes |

---

## <what maps to the research>

### 2305.14325 (Multi-Agent Debate): Teams enables the mechanism, but barely

The debate paper validates multi-round deliberation between LLM agents. Agent Teams provides the SendMessage primitive that makes this possible. But the paper used 3-6 agents in experiments. The stubbornness finding ("stubborn prompts produce longer debates and better outcomes") maps to structured archetype personas, which can be encoded in spawn prompts. The agreeableness warning ("RLHF makes agents converge too quickly") maps to the TeammateIdle hook -- if an archetype tries to idle after premature agreement, the hook can force continued deliberation.

However: the paper's debate mechanism is simple (concatenate all responses, present to each agent). Agent Teams' messaging is more complex (discrete SendMessage calls between specific agents). This is actually an advantage -- it enables the coordinator-mediated pairing in rounds 3-4 where specific archetypes debate each other.

### 2402.19379 (Silicon Crowd): Teams' Broadcast is the threat vector

The ensemble paper's central finding -- that simple averaging beats LLM updating (p=0.011) -- means that EVERY Broadcast in OathFish is a potential accuracy-destroying event. When archetypes see each other's arguments via Broadcast or coordinator-relayed SendMessage, they anchor and adjust. The v3 redesign's "arguments-only, no numbers until round 6" mitigates this, but the Teams architecture makes it trivially easy for the coordinator or any archetype to accidentally share numeric predictions in messages. There is no enforcement mechanism in Teams to prevent this -- it would require hook-based validation of every message, and the docs do not describe message-content hooks.

The 57% acquiescence rate is especially dangerous at scale: 30 agents converging toward positive predictions via Broadcast-mediated social influence produces systematic bias that amplifies rather than cancels.

### 2409.19839 (ForecastBench): Teams adds overhead that may not earn its keep

The ForecastBench paper shows superforecasters at Brier 0.096 and best LLM at 0.1352. The gap OathFish must close is ~0.04 Brier points. Running 30 Team members for 6 rounds to achieve this requires the deliberation to add genuine reasoning value. But Teams' coordination overhead (token cost, latency, message passing) means the cost per Brier point improvement is astronomical. A smaller team (5 archetypes) doing the same deliberation protocol at 1/6th the cost might achieve the same improvement. The "combination questions benefit most" finding suggests deliberation's value concentrates on a subset of questions -- running 30 agents on every question is wasteful.

### Cross-paper synthesis: the v3 redesign's subagent proposal is architecturally incoherent

The research-driven-redesign.md (WARNING-01 mitigation) proposes: "Moving archetypes to persistent subagents (not all Team members) reduces Team size. Coordinator in Team; archetypes as subagents spawned per round."

But the docs are explicit: subagents "only report results back to the main agent and never talk to each other." The debate paper (2305.14325) requires inter-agent communication for reasoning improvement. If archetypes are subagents, they cannot debate each other. The coordinator would need to manually relay every message between every pair of archetypes by receiving a response from subagent A, forwarding it to subagent B, receiving B's response, forwarding to A, etc. This is technically possible but:
- Coordinator's context window becomes the bottleneck (receives ALL 30 agents' messages)
- No parallelism in debate exchanges (coordinator is the serial relay point)
- Coordinator's context fills rapidly with 30 agents x 6 rounds of relayed messages
- Subagents cannot self-coordinate -- coordinator must explicitly manage every interaction

The subagent approach trades the Teams scale problem for a coordinator bottleneck problem. Neither architecture cleanly supports 30-agent structured debate.

---

## <what 10x the outcome>

The 10x insight is: **OathFish should not use Teams for 30 parallel agents. It should use Teams for 5-6 "perspective cluster leads" that each represent a coalition of archetypes, with the actual 30 archetypes implemented as subagents spawned per round by their cluster lead.**

### Architecture: Hierarchical Teams + Subagent Swarms

```
Team Lead (Coordinator)
  |
  ├── Teammate 1: "Capital Perspective" (VC, Angel, PE, Fund-of-Funds, Corporate Dev)
  |     └── spawns 5 subagents per round for detailed archetype reasoning
  |
  ├── Teammate 2: "Builder Perspective" (Founder, CTO, IC Engineer, PM, Designer)
  |     └── spawns 5 subagents per round
  |
  ├── Teammate 3: "Regulator Perspective" (Policymaker, Lawyer, Compliance, Ethicist, Auditor)
  |     └── spawns 5 subagents per round
  |
  ├── Teammate 4: "Consumer Perspective" (Early Adopter, Mainstream, Skeptic, Enterprise Buyer, SMB)
  |     └── spawns 5 subagents per round
  |
  ├── Teammate 5: "Ecosystem Perspective" (Academic, Media, Lobbyist, Competitor, Incumbent)
  |     └── spawns 5 subagents per round
  |
  └── Teammate 6: Report Analyst
        └── synthesizes all outputs
```

Why this is 10x:

1. **Stays within recommended Teams range (6 teammates).** No heroic scaling assumptions.
2. **Cluster leads CAN debate each other via SendMessage.** This gives you 5-way inter-perspective deliberation -- which may be the actual effective ensemble size anyway (paper-ensemble: "effective ensemble size may be 3-5, not 30" due to single-model correlation).
3. **Subagents provide the 30-agent depth.** Each cluster lead spawns 5 archetype subagents per round to do detailed reasoning. Subagents report back to their cluster lead, who synthesizes and represents the perspective in the Team debate.
4. **Subagents can have memory:project.** Persistent cross-run learning for each archetype, which Team members cannot do.
5. **Round management becomes tractable.** Coordinator manages 5 debate participants, not 30. The structured debate in rounds 3-4 involves pairing 5 cluster leads, not 30 archetypes.
6. **Cost is dramatically lower.** 6 Team members + 30 subagents spawned per round (not persistent) vs 32 permanent Team members.
7. **Matches the research.** The debate paper used 3-6 agents. The ensemble paper showed effective ensemble size of 3-5. A 5-way Team debate is in the sweet spot.
8. **Cluster leads aggregate internal diversity.** Each cluster lead receives 5 diverse archetype perspectives before entering the Team debate. This means the Team debate operates on pre-synthesized positions that already incorporate diversity within each perspective cluster.

### Round flow under hierarchical architecture

```
Round 1-2 (FREE_FORM):
  Coordinator broadcasts prompt to 5 cluster leads
  Each cluster lead spawns 5 archetype subagents
  Subagents reason and report back to cluster lead
  Cluster lead synthesizes into perspective statement
  Cluster lead sends perspective to coordinator via SendMessage
  Coordinator compiles and broadcasts all 5 perspectives

Round 3-4 (STRUCTURED_DEBATE):
  Coordinator pairs cluster leads (Capital vs Regulator, etc.)
  Cluster leads debate via direct SendMessage
  Each cluster lead can consult their subagents mid-debate
  Structured stubbornness at the CLUSTER level, not individual level

Round 5 (SCENARIO_INJECTION):
  Coordinator injects scenario to all cluster leads
  Each cluster lead spawns subagents to stress-test from their angle
  Cluster leads report second-order effects

Round 6 (INDEPENDENT_PREDICTION):
  Each cluster lead's 5 subagents independently produce JSON predictions
  30 independent predictions (5 per cluster x 6 clusters) -- MINUS report analyst
  Aggregate via median
  No inter-cluster number sharing
```

This preserves the entire v3 deliberation protocol while fitting cleanly into Agent Teams' actual capabilities.

---

## <why?>

Three forces converge to make this the right architecture:

**Force 1: Teams' documented capabilities.** The docs say 3-5 teammates, recommend against scaling up, and provide zero evidence of Teams working at 30+ agents. The hierarchical approach keeps the Team at 6 -- solidly within the recommended range. Every capability OathFish needs (SendMessage debate, Broadcast rounds, TeammateIdle hooks, plan approval) works as documented at this scale.

**Force 2: The research on effective ensemble size.** Paper-ensemble (2402.19379) and the final synthesis both warn that 30 Claude instances share training data and RLHF objectives. The effective ensemble size may be 3-5, not 30. If this is true, then a 5-way Team debate between cluster leads captures nearly ALL the ensemble diversity, and the 30 subagents within clusters provide the depth/coverage that improves the quality of each perspective rather than adding independent signal. This means OathFish's value comes from DEPTH within perspectives (subagents) + BREADTH across perspectives (Team debate), not from 30 supposedly independent voices.

**Force 3: The coordinator bottleneck is real.** Managing 30 simultaneous message threads, tracking argument evolution across 180+ exchanges, pairing archetypes for structured debate, monitoring diversity index -- all through natural language instructions to a Team lead -- is a prompt engineering nightmare. At 5 cluster leads, the coordinator's job is tractable: 5 threads, 5 perspectives to track, 10 pairings for structured debate. The complexity reduction is combinatorial: pairing 30 agents = 435 possible pairs. Pairing 5 = 10.

**The research explicitly supports this.** The debate paper (2305.14325) used 3-6 agents. The ensemble paper found effective diversity tops out at 3-5 with a single model. The ForecastBench paper showed the gap to close is ~0.04 Brier -- achievable through reasoning depth, not agent count. The persona paper showed 85% fidelity comes from grounding quality, not quantity. Every paper points to "fewer, deeper" over "more, shallower."

---

## <reality check?>

### Is 32 agents in a Team realistic?

**No.** The docs recommend 3-5 and explicitly warn about diminishing returns. There is no documented example of a Team with more than 5 members. C-18 ("Claude Teams ~30 concurrent agents maximum") appears to be an OathFish assumption, not a documented Anthropic limitation. The actual constraint is not a hard cap but a practical ceiling: token cost, coordination overhead, and context window limits make 32-agent Teams impractical even if technically possible.

Specific risks at 32 agents:
- **Token cost**: 32 concurrent Opus/Sonnet sessions running for 6+ rounds. At $15/MTok input and $75/MTok output for Opus, a single OathFish run could cost hundreds of dollars in API tokens.
- **Coordination collapse**: The lead must manage 32 simultaneous threads. Its context window fills with message traffic. At ~200K tokens of context, 32 agents each sending multi-paragraph arguments every round will fill the lead's context within 2-3 rounds.
- **Broadcast amplification**: "Broadcast costs scale with team size." Broadcasting to 32 agents means 32 message deliveries per broadcast. 6 rounds with multiple broadcasts per round = potentially hundreds of broadcast deliveries.
- **No evidence it works**: The docs provide examples with 3-5 teammates. Zero examples, zero benchmarks, zero guidance for teams of 30+.

### Is the v3 subagent proposal viable?

**Partially.** Moving archetypes to subagents solves the Team scale problem but creates two new problems:
1. Subagents cannot communicate with each other (docs are explicit). All debate must be relayed through the coordinator, creating a serial bottleneck.
2. Subagents cannot spawn other subagents. This limits the architecture to two levels (coordinator -> archetypes). The hierarchical approach I propose requires teammates to spawn subagents, and the docs do not address whether teammates can spawn subagents (they say teammates cannot spawn *teams*, but subagents are different from teams).

**Critical unknown**: Can a Team member (teammate) invoke subagents? The docs say:
- "Teammates cannot spawn their own teams" (no nested Teams)
- "Subagents CANNOT spawn other subagents" (from sub-agents reference)
- But teammates are full Claude Code sessions, which implies they can use subagents

If teammates CAN spawn subagents, the hierarchical architecture works perfectly. If they CANNOT, the proposal collapses to either: (a) all 30 archetypes as Team members (scale problem), or (b) all 30 archetypes as subagents of the coordinator (communication problem).

**This is the single most important technical question to validate before building.**

### Is the feature stable enough to build on?

**No.** The docs explicitly state: "Agent teams are experimental and disabled by default." The warning lists known limitations around session resumption, task coordination, and shutdown behavior. Building OathFish's core deliberation architecture on an experimental feature means:
- API may change without notice
- Features may be removed
- Performance may be unpredictable
- Bug reports will be competing with Anthropic's own development priorities

The mitigation is to build OathFish's deliberation protocol as an abstraction layer ABOVE Agent Teams, so the underlying coordination mechanism can be swapped if Teams is deprecated or changed.

### Will the TeammateIdle hook actually enforce deliberation?

**Probably.** The hook fires when a teammate is "about to go idle" and exit code 2 keeps them working. This could enforce continued participation in deliberation rounds. But the docs do not explain what "go idle" means precisely -- does it mean the teammate has no more tasks? Has finished its current turn? Is waiting for a message? If "idle" means "no tasks to claim," then archetypes without pending tasks would trigger the hook even during normal between-round pauses. The hook semantics need testing.

### Is the experimental flag likely to be removed soon?

**Unknown, but probable.** The docs mention version 2.1.32 as the minimum, and the feature is comprehensive enough (display modes, hooks, task system, messaging) to suggest it has been in development for a while. But "experimental" means Anthropic has not committed to the API surface. The hierarchical architecture reduces this risk by depending on Teams for only 6 members (basic functionality) rather than 32 (pushing limits).

---

## <citations from the references document>

### From the Agent Teams documentation (primary source)

> "Agent teams are experimental and disabled by default. Enable them by adding CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS to your settings.json or environment."

> "There's no hard limit on the number of teammates, but practical constraints apply: Token costs scale linearly [...] Coordination overhead increases [...] Diminishing returns: beyond a certain point, additional teammates don't speed up work proportionally."

> "Start with 3-5 teammates for most workflows. This balances parallel work with manageable coordination."

> "Having 5-6 tasks per teammate keeps everyone productive without excessive context switching."

> "Three focused teammates often outperform five scattered ones."

> "Teammates cannot spawn their own teams or teammates. Only the lead can manage the team."

> "Each teammate has its own context window. When spawned, a teammate loads the same project context as a regular session: CLAUDE.md, MCP servers, and skills. It also receives the spawn prompt from the lead. The lead's conversation history does not carry over."

> "message: send a message to one specific teammate. broadcast: send to all teammates simultaneously. Use sparingly, as costs scale with team size."

> "Unlike subagents, which run within a single session and can only report back to the main agent, you can also interact with individual teammates directly without going through the lead."

> "Use subagents when you need quick, focused workers that report back. Use agent teams when teammates need to share findings, challenge each other, and coordinate on their own."

### From research-driven-redesign.md (v3 proposal)

> "Moving archetypes to persistent subagents (not all Team members) reduces Team size. Coordinator in Team; archetypes as subagents spawned per round. This sidesteps the 32-member limit entirely." (WARNING-01 mitigation)

> "Archetypes as persistent subagents [...] memory: project — Cross-run learning" (Section 4.2.2)

### From spec-audit.md (blocking issues)

> "WARNING-01: Claude Teams Scale at 32 Members (HIGH) — Persistent subagent architecture (v3 change) may mitigate this if archetypes are spawned per-round rather than kept as permanent Team members. However, the spec says 'All 30 archetype agents remain alive in the Team' for the INTERACT phase."

> "C-04: Claude Teams with 30 archetypes via SendMessage — FEASIBLE with WARNING — Max tested ~10; 32 is untested"

### From sub-agents reference (communication constraint)

> "Subagents CANNOT spawn other subagents. Only agents running as main thread with claude --agent can spawn subagents."

### From final-synthesis.md (ensemble diversity)

> "Single-model correlated failures reducing effective ensemble to 3-5" (Risk #2)

> "30 Claude instances share training data and RLHF objectives" (WARNING-07)

### From 2305.14325 (debate paper)

> "Prompts that encouraged models to be more 'stubborn' (trust their own solutions more) led to LONGER debates and BETTER final solutions"

> "Language model agents are relatively 'agreeable', perhaps as a result of instruction tuning or RLHF — they converge TOO QUICKLY"

### From 2402.19379 (ensemble paper)

> "Simple average of human+machine predictions BEATS the LLM's own update: GPT-4 p=0.011, Claude 2 p=0.001"

> "Mean model predictions significantly above 50%: M=57.35, t(1006)=86.20, p<0.001"

### From 2409.19839 (ForecastBench)

> "Expert forecasters significantly outperform best LLMs (p < 0.001)"

> "Best superforecasters: ~0.096. o3 (best LLM as of 2025): 0.1352"
