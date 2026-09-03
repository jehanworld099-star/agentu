# Prompt: Social post from a completed blueprint

Used by: `scenarios/growth-agent/portfolio-update.blueprint.json` (draft
stage only — publishing is gated the same as outreach, see
`docs/growth-agent/compliance-and-approval.md`)
Implements: `GROWTH_AGENT_SYSTEM_PROMPT.md` Module 5

## Inputs

- `completed_engagement`: the `solution_blueprint` and outcome metrics for
  a converted, completed client engagement, plus confirmation the client
  approved being referenced (even in anonymized/conceptual form).
- `platform`: which channel this post is for (affects length/tone).

## Instructions

```
Write a social post showcasing the conceptual workflow from
{{completed_engagement.solution_blueprint.summary}}, for {{platform}}.

Outcome (if available): {{completed_engagement.outcome_metrics}}

Rules:
- Explain the concept and the outcome, not the client's confidential
  specifics — no client name, no identifying detail, unless
  completed_engagement explicitly says the client approved being named.
- Teach something real (the underlying idea), don't just brag — this is
  authority-building content, not an ad.
- Match {{platform}}'s norms: shorter/punchier for X, more explanatory for
  LinkedIn, avoid banned AI-tell phrases listed in
  prompts/growth-agent/cold-outreach.md throughout.
- No fabricated metrics — use only what's in outcome_metrics, or omit
  numbers entirely if none are available/confirmed.

Output the post text only, ready to review.
```
