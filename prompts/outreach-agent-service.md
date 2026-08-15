# Prompt: Outreach draft — agent-service pitch

Used by: `scenarios/lead-qualification.blueprint.json` (draft stage only —
sending is gated, see `docs/approval-thresholds.md`)
Implements: System prompt §5 "Agent Self-Promotion & Sales"

## Inputs

- `prospect`: qualified lead record, including `pain_signals` from the
  qualification step.
- `sender_profile`: who's pitching, and a one-line description of the
  agent/service being sold.

## Instructions

```
Draft a short outreach message pitching the social media management
automation agent to {{prospect.name}}.

Why they were flagged:
{{prospect.reasoning}}
{{prospect.pain_signals}}

Sender: {{sender_profile}}

Rules:
- Open with the specific pain signal observed, not a generic capability
  list.
- Explain the value in one sentence: what stops happening for them (missed
  replies, inconsistent posting) once this runs.
- One clear, low-friction call to action — e.g. offering a short demo or a
  one-week trial on one platform.
- Under 90 words. No exclamation-point salesiness. No emojis.

Output the message text only, ready to send as-is.
```
