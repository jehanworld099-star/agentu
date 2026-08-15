# Prompt: Growth & strategy report

Used by: `scenarios/growth-report.blueprint.json`
Implements: System prompt §3 "Growth & Strategy Suggestions"

## Inputs

- `metrics`: per-account time series (posts, reach, engagement rate,
  follower delta) for Facebook, Instagram, YouTube, for the report period.
- `flagged_accounts`: output of the platform-health-check scenario (§1).
- `period`: `weekly` or `monthly`, with start/end dates.

## Instructions

```
You are producing a {{period}} growth report for {{business_profile.name}}
covering Facebook, Instagram, and YouTube.

Metrics for the period:
{{metrics}}

Accounts flagged as inactive or underperforming this period:
{{flagged_accounts}}

Write a report with these sections:
1. Headline summary — 2-3 sentences, what moved and why it matters.
2. Per-platform performance — key numbers, trend vs. prior period.
3. Flagged accounts — what's wrong and a specific fix, not just "post more".
4. Best posting times — derived from the engagement data provided, not
   generic advice; say "insufficient data" if the sample is too small
   rather than inventing a pattern.
5. Content format & trend opportunities — specific, actionable, tied to
   what's actually working in the data or genuinely observable platform
   trends — no generic filler like "post more Reels".
6. Hashtag/keyword opportunities — specific terms, not categories.
7. Next {{period}}'s top 3 actions — ranked by expected impact.

Keep it concise enough to read in under 3 minutes. No padding.
```
