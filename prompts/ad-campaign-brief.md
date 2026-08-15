# Prompt: Ad campaign brief

Used by: `scenarios/ad-campaign-launch.blueprint.json`
Implements: System prompt §6 "Facebook Ads Management"

## Inputs

- `business_goal`: free-text goal from the business owner (e.g. "more
  bookings this week", "sell remaining inventory of X").
- `business_profile`: brand voice, target market description, past
  campaign performance if any.
- `available_creative`: images/video assets and existing ad copy on hand.

## Instructions

```
Turn this goal into a structured Facebook/Instagram ad campaign brief for
{{business_profile.name}}.

Goal: {{business_goal}}
Business/market context: {{business_profile}}
Available creative: {{available_creative}}

Produce:
1. Objective — map to a Meta campaign objective (awareness, traffic,
   engagement, leads, sales) that best fits the goal.
2. Audience — location, age range, interests/behaviors, and whether a
   lookalike/retargeting audience is appropriate given available data.
3. Budget — daily budget recommendation and rationale, and campaign
   duration.
4. Creative — which available asset to use, or what's missing; ad copy
   (headline, primary text, CTA) on-brand and specific to the offer.
5. Success metric — the one number that defines whether this campaign
   worked, tied to the original goal.

Output as JSON matching the campaign-brief shape the Make.com Facebook Ads
modules expect: {objective, audience, budget: {daily, currency, duration_days},
creative: {asset_ref, headline, primary_text, cta}, success_metric}.

Do not mark this brief as ready-to-launch — that decision is made by the
approval gate in docs/approval-thresholds.md, not by this prompt.
```
