# Prompt: Portfolio case study writeup

Used by: `scenarios/growth-agent/portfolio-update.blueprint.json`
Implements: `GROWTH_AGENT_SYSTEM_PROMPT.md` Module 5

## Inputs

- `completed_engagement`: prospect record at `status: "converted"`,
  including `audit_brief`, `solution_blueprint`, and any outcome metrics
  the client has shared and approved for external use.

## Instructions

```
Write a portfolio case study for the completed engagement below.

Before state (from the original audit):
{{completed_engagement.audit_brief}}

What was built:
{{completed_engagement.solution_blueprint}}

Outcome:
{{completed_engagement.outcome_metrics}}

Structure:
1. The problem — 2-3 sentences, grounded in the actual audit_brief gaps,
   written for a prospective client skimming the portfolio (not the
   original client).
2. The build — plain-language walkthrough of solution_blueprint, what it
   automates and why each piece matters, no unexplained jargon.
3. The result — only outcome_metrics actually provided; if none were
   shared, write "Results tracking in progress" rather than inventing a
   number.

Use the client's name/logo only if completed_engagement confirms explicit
permission was given; otherwise refer to them by niche + rough size (e.g.
"a 12-person e-commerce skincare brand").

Output as markdown, ready to drop into the portfolio.
```
