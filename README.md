# OathFish - Swarm Intelligence Prediction Engine for Claude Code

OathFish is a Claude Code plugin that runs multi-agent deliberation between population archetypes to produce structured ensemble predictions. It combines superforecasting methodology with swarm intelligence: diverse archetype agents debate a question, then their evolved positions are mass-amplified to produce statistically grounded predictions with reasoning chains.

## Installation

```bash
# Add to Claude Code
claude plugin add oathe-ai/oathfish

# Or clone and install locally
git clone https://github.com/oathe-ai/oathfish.git
claude plugin add ./oathfish
```

## Quick Start

```bash
# Run a full prediction
/oathfish "Will the EU AI Act reduce startup formation by >25% by 2028?"

# With custom parameters
/oathfish "How will remote work trends affect commercial real estate?" --archetypes 10 --rounds 3 --amplify 50

# Chat with archetypes after a run
/oathfish-chat "What does the Historian think about the GDPR precedent?"
```

## How It Works

```
UNDERSTAND ──> BASELINE_AMPLIFY ──> DELIBERATE ──> AMPLIFY ──> SYNTHESIZE
    │                │                   │              │            │
    │                │                   │              │            │
 Analyze topic   Pre-deliberation    Multi-round     Post-delib   Generate
 Generate 30     stateless baseline  archetype       informed     prediction
 archetypes      (A/B control)       debate          amplification report
```

### Pipeline Phases

1. **UNDERSTAND** -- Analyzes the question, identifies stakeholder segments, generates 30 archetype personas (4 structural + 26 topic-customized) with source grounding.
2. **BASELINE_AMPLIFY** -- Runs stateless mass amplification with initial archetype stances before deliberation, establishing the simple-averaging baseline for A/B comparison.
3. **DELIBERATE** -- Multi-round deliberation where archetypes argue, challenge, and evolve positions. Rounds alternate between free-form argument and structured prediction.
4. **AMPLIFY** -- Post-deliberation mass amplification using evolved positions. Compared against baseline to measure deliberation's value.
5. **SYNTHESIZE** -- Produces the final prediction report with reasoning chains, statistical distributions, and calibration data.

### The 4 Structural Archetypes

Every run includes four mandatory epistemic lenses (not stakeholder personas):

| Archetype | Role |
|-----------|------|
| **Historian** | Anchors to historical base rates and precedent |
| **Systems Thinker** | Maps feedback loops, second-order effects, cascade dynamics |
| **Contrarian** | Challenges emerging consensus with reasoned dissent |
| **Probabilist** | Calibrates uncertainty, tracks Bayesian updates, flags overconfidence |

## MCP Engine

OathFish includes a deterministic computation engine exposed via MCP tools:

- **State management** -- Run lifecycle, checkpoints, resume
- **Deliberation tracking** -- Round recording, position evolution, convergence detection
- **Amplification** -- Batch recording, statistical aggregation, A/B comparison
- **Calibration** -- Prediction recording, outcome resolution, domain/archetype bias tracking
- **Competence classification** -- Domain routing, complexity assessment

## Output Artifacts

```
runs/{RUN_ID}/
  _meta/
    run.json                      # State machine, config, transition history
  understanding/
    archetypes.json               # 30 archetype definitions with grounding
    topic-analysis.md             # Question decomposition
    competence.json               # Domain classification
  amplification/
    baseline/                     # Pre-deliberation control group
    informed/                     # Post-deliberation treatment group
  deliberation/
    round-{N}/                    # Per-round archetype positions
  synthesis/
    prediction-report.md          # Executive summary + reasoning chains
    statistics.md                 # Per-archetype distributions
    calibration.md                # Brier scores (when outcomes resolve)
    diversity-trajectory.md       # Per-round diversity metrics
```

## Project Structure

```
oathfish/
  .claude-plugin/plugin.json      # Plugin manifest
  engine/                         # MCP server (Python, Pydantic models)
  agents/                         # Archetype agent definitions
  skills/                         # Phase skills (understand, deliberate, etc.)
  commands/                       # Slash commands (/oathfish, /oathfish-chat)
  hooks/                          # SessionStart, PreCompact state injection
  scripts/                        # Utility scripts
  references/                     # Claude Code feature documentation
  tests/                          # Engine unit tests
```

## Commands

| Command | Description |
|---------|-------------|
| `/oathfish "<question>"` | Run full prediction pipeline |
| `/oathfish-chat` | Chat with archetypes from a completed run |
| `/oathfish-evaluate` | Evaluate a run against architectural compliance checklist |

## Key Design Principles

- **Epistemic lenses, not stakeholder personas** -- Structural archetypes reason from methodology (base rates, feedback loops, calibration), not self-interest
- **A/B deliberation testing** -- Every run compares pre- vs post-deliberation predictions to prove deliberation adds value
- **Structured amplification** -- Mass samples via `claude -p --json-schema` for stateless, schema-enforced predictions
- **Convergence detection** -- Deliberation stops when positions stabilize, preventing both premature consensus and endless debate
- **Source grounding** -- Every archetype cites real sources (Rung 1-4 grounding quality)

## License

MIT
