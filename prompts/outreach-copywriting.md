# Prompt: Outreach draft — copywriting pitch

Used by: `scenarios/lead-qualification.blueprint.json` (draft stage only —
sending is gated, see `docs/approval-thresholds.md`)
Implements: System prompt §4 "Copywriting Client Acquisition"

## Inputs

- `prospect`: qualified lead record (see `schemas/lead.schema.json`),
  including `weak_copy_examples` from the qualification step.
- `sender_profile`: who's pitching — name/brand, portfolio link, rate
  range if applicable.

## Instructions

```
Draft a short, specific outreach message pitching copywriting services to
{{prospect.name}}.

Context on why they were flagged:
{{prospect.reasoning}}
{{prospect.weak_copy_examples}}

Sender: {{sender_profile}}

Rules:
- Reference something real and specific about their existing content —
  never a generic "I noticed your business could use better copy."
- Lead with a concrete observation, not a sales pitch — the value should
  be obvious before the ask.
- One clear, low-friction call to action (e.g. "want me to rewrite one
  product description for free so you can see the difference?").
- Under 80 words. No exclamation-point salesiness. No emojis.

Output the message text only, ready to send as-is.
```
