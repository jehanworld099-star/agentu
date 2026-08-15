# Prompt: Lead qualification — copywriting clients

Used by: lead-sourcing scenario feeding
`scenarios/lead-qualification.blueprint.json`
Implements: System prompt §4 "Copywriting Client Acquisition"

## Inputs

- `prospect`: public profile data — business name, platform(s), sample
  captions/ad copy/product descriptions, follower count, posting
  frequency.

## Instructions

```
Evaluate whether {{prospect.name}} is a good-fit lead for copywriting
services (ad copy, product descriptions, social captions).

Prospect data:
{{prospect}}

Score against:
1. Business size — active, real business, plausible budget for a
   copywriter (not a hobby account, not enterprise with an in-house team).
2. Current content quality — weak/generic/typo-ridden copy is a positive
   signal for this offer; already-strong, distinctive copy is a negative
   signal.
3. Platform activity — active enough that better copy would visibly move
   metrics; a dormant account is a weak lead regardless of copy quality.

Output as JSON:
{
  "qualified": true | false,
  "score": 0-100,
  "reasoning": "<2-3 sentences, specific to this prospect's actual content>",
  "weak_copy_examples": ["<verbatim excerpt>", ...]
}
```

## Notes

- `qualified: true` requires score >= 60 by default (tune per business).
- Only use publicly available content already visible on the prospect's
  page/profile — do not fabricate examples.
