---
name: oathfish-chat
description: "Chat with any archetype from a completed OathFish deliberation, or with the report analyst. Archetypes respond in-character with full deliberation memory."
argument-hint: '--archetype "The Cautious VC" OR --report'
---

Route this chat request to the OathFish interact skill.

User request: $ARGUMENTS

Parse the arguments to determine the target:
- If --archetype "Name": resume that archetype subagent with the message
- If --report: resume the report analyst with the message
- If neither flag: send to the report analyst as a general follow-up
