# Prompt: Lead qualification — agent-as-a-service prospects

Used by: `scenarios/lead-qualification.blueprint.json`
Implements: System prompt §5 "Agent Self-Promotion & Sales"

## Inputs

- `prospect`: public profile data — business name, platforms present on,
  posting cadence, response time to customer comments/DMs where
  observable, evidence of manual/ad-hoc social management (inconsistent
  posting, slow replies, single-platform presence when multi-platform
  would help).

## Instructions

```
Evaluate whether {{prospect.name}} would benefit from a unified social
media management + sales automation agent like this one (multi-platform
posting/monitoring, unified WhatsApp customer support, growth reporting,
ad management).

Prospect data:
{{prospect}}

Score against:
1. Pain signals — inconsistent posting, slow or missed replies to
   comments/DMs, presence on some but not all relevant platforms, no
   visible ad activity despite an active page.
2. Capacity to act — real operating business, plausible budget for a
   monthly automation service, decision-maker likely reachable via the
   page/profile itself.
3. Fit — business type suits ongoing social + WhatsApp support (local
   service business, e-commerce, etc.) rather than one that wouldn't need
   it (e.g. B2B enterprise with existing dedicated marketing staff).

Output as JSON:
{
  "qualified": true | false,
  "score": 0-100,
  "reasoning": "<2-3 sentences, specific to this prospect>",
  "pain_signals": ["<specific observed signal>", ...]
}
```
