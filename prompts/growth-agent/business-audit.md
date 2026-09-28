# Prompt: Deep business audit — Client Diagnostics Brief

Used by: `scenarios/growth-agent/business-audit.blueprint.json`
Implements: `GROWTH_AGENT_SYSTEM_PROMPT.md` Module 2

## Inputs

- `prospect`: business name, website URL, niche, country.
- `website_content`: fetched HTML/text of the prospect's homepage and any
  linked contact/about/product pages.
- `ad_library_result`: raw result of the Meta Ad Library lookup for this
  Page, if a Facebook Page was identified (may be empty/null if none
  found).

## Instructions

```
Audit {{prospect.name}}'s public digital presence using only the material
provided below. Do not infer or assume anything not evidenced in the
content itself.

Website content:
{{website_content}}

Meta Ad Library result:
{{ad_library_result}}

Produce a Client Diagnostics Brief as JSON:
{
  "ad_status": "running" | "not_running" | "low_quality",
  "ad_status_evidence": "<what in ad_library_result supports this>",
  "copywriting_gaps": [
    "<specific gap, quoting or closely paraphrasing the actual weak copy
      found — e.g. 'Homepage hero headline is a feature list
      (\"Premium organic skincare products\") with no hook or emotional
      angle'>"
  ],
  "marketing_gaps": [
    "<specific structural gap — e.g. 'No visible retargeting pixel or
      email capture on the homepage; a visitor who leaves has no way to
      be brought back'>"
  ],
  "contact_email_found": "<a role-based or general inbox found on the
    site itself, e.g. hello@company.com, or null if none visible>",
  "overall_fit": "strong" | "moderate" | "weak",
  "overall_fit_reasoning": "<1-2 sentences>"
}

Rules:
- Every gap must cite something actually observed in website_content —
  no generic gaps that could apply to any business.
- If website_content is too thin to assess (e.g. fetch failed, near-empty
  page), set overall_fit to "weak" and say why rather than guessing.
- contact_email_found must come only from what's visible in
  website_content (e.g. a contact page or footer) — never fabricated.
```

## Notes

- This brief becomes the input to `prompts/growth-agent/solution-blueprint.md`
  and `prompts/growth-agent/cold-outreach.md` — vague or generic output
  here degrades both downstream steps, so specificity is the main quality
  bar to enforce.
