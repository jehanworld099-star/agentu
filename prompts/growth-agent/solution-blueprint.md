# Prompt: Solution blueprint design

Used by: `scenarios/growth-agent/solution-blueprint.blueprint.json`
Implements: `GROWTH_AGENT_SYSTEM_PROMPT.md` Module 3

## Inputs

- `prospect`: business name, niche.
- `audit_brief`: the Client Diagnostics Brief from Module 2
  (`prompts/growth-agent/business-audit.md` output).

## Instructions

```
Design a no-code automation blueprint that fixes the specific gaps found
for {{prospect.name}}.

Diagnostics brief:
{{audit_brief}}

Output as JSON:
{
  "summary": "<2-3 sentences: what this blueprint does for them and the
    outcome it targets, in plain language a non-technical business owner
    would understand>",
  "modules": [
    {
      "step": 1,
      "trigger_or_action": "<e.g. 'New Shopify order' or 'Contact form
        submission'>",
      "tool": "<Make.com module / app name, or n8n node name>",
      "purpose": "<which specific gap from audit_brief this addresses>",
      "api_or_integration": "<free/low-cost API or integration needed,
        e.g. 'Meta Conversions API (free)', 'Mailchimp API (free tier)'>"
    }
  ],
  "addresses_gaps": ["<gap from audit_brief>", "..."],
  "estimated_build_complexity": "low" | "medium" | "high"
}

Rules:
- Every module in the flow must trace back to a specific gap in
  audit_brief via addresses_gaps — no generic "add a CRM" filler steps
  that don't map to an observed problem.
- Prefer free or low-cost APIs/tools where a reasonable one exists; note
  when a paid tool is genuinely the best fit and why.
- This is a design document for a human to build from, not a runnable
  scenario — do not output actual Make.com blueprint JSON here.
```
