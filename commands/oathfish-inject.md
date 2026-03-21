---
name: oathfish-inject
description: "Inject an event into an active OathFish deliberation. Triggers a scenario reaction round where all archetypes reason about the event's impact."
argument-hint: '"Breaking: Major competitor raises $500M" --run RUN_ID'
disable-model-invocation: true
---

Inject this event into the active OathFish deliberation: $ARGUMENTS

This triggers a SCENARIO_REACTION round where all 30 archetypes reason about
second-order effects of this event on their population segment.

Parse arguments:
- First argument: the event description (quoted string)
- --run RUN_ID: optional, defaults to active run
