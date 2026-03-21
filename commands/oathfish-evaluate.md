---
name: oathfish-evaluate
description: "Evaluate a completed OathFish run against architectural requirements. Produces a compliance scorecard with PASS/FAIL per checklist item."
argument-hint: 'RUN_ID (e.g., run-20260318-150156)'
disable-model-invocation: true
---

Evaluate the specified OathFish run: $ARGUMENTS

Invoke the evaluate skill: Skill(skill="oathfish:evaluate", args="$ARGUMENTS")
