# agentu — Unified Social Media Management & Sales Agent

`agentu` is a coordinated automation agent that manages a business's Facebook
Pages, Instagram Pages, YouTube channels, and WhatsApp customer support as a
single system, and drives two sales motions on top of that (copywriting
client acquisition and agent-as-a-service self-promotion), plus Facebook/
Instagram ads.

The canonical behavior spec is [`SYSTEM_PROMPT.md`](./SYSTEM_PROMPT.md).
Everything else in this repo implements one piece of that spec.

`agentu` also includes a more detailed **growth/client-acquisition module** —
find prospects who need AI automation help, audit them, design a tailored
solution, draft (never auto-send) outreach, and grow the agency's own
portfolio. Its canonical spec is
[`GROWTH_AGENT_SYSTEM_PROMPT.md`](./GROWTH_AGENT_SYSTEM_PROMPT.md); see that
file and [`docs/growth-agent/`](./docs/growth-agent/) before touching
anything under `scenarios/growth-agent/` or `prompts/growth-agent/`.

## Repository layout

```
SYSTEM_PROMPT.md              Canonical agent system prompt — source of truth
GROWTH_AGENT_SYSTEM_PROMPT.md Canonical spec for the client-acquisition module
docs/
  architecture.md             How each responsibility maps to Make.com scenarios / APIs
  approval-thresholds.md      Approval gates for irreversible actions (spend, bulk outreach)
  escalation.md               What gets escalated to a human, and how
  growth-agent/
    architecture.md            Module-by-module implementation for lead→portfolio pipeline
    data-sourcing-policy.md    Where leads/emails legally come from (no platform scraping)
    compliance-and-approval.md Per-message approval rule + international cold-email law notes
scenarios/
  *.blueprint.json             Make.com scenario blueprint stubs, one per responsibility
  growth-agent/*.blueprint.json Blueprint stubs for the client-acquisition pipeline
prompts/
  *.md                        Reusable prompt templates the agent uses for each task
  growth-agent/*.md            Prompt templates for audit/blueprint/outreach/portfolio
schemas/
  action-log.schema.json      JSON schema for the action log (§ "Log every action taken")
  lead.schema.json             JSON schema for lead/outreach tracking records (all tracks)
config/
  platforms.example.json       Env-var-referenced config for connected accounts (no secrets)
```

## Setup

1. **Connect accounts.** In Make.com, create connections for: Facebook Pages,
   Instagram, YouTube Data API, and WhatsApp Business Cloud API. Copy
   `config/platforms.example.json` to `config/platforms.json` and fill in the
   Page/Channel/Business IDs (not secrets — those live in Make.com's
   connection store or your secret manager, never in this repo).
2. **Import scenario stubs.** Each file in `scenarios/` is a minimal, valid
   Make.com blueprint skeleton for one responsibility (inbound message
   routing, growth reporting, lead capture, ad launch, etc.). Import it into
   Make.com and wire in the real modules/connections for your account.
3. **Set approval thresholds.** Edit `docs/approval-thresholds.md` before
   turning on anything that spends money or sends outreach at scale — the
   agent must never cross these without a human sign-off, per the system
   prompt's Operating Principles.
4. **Wire up logging.** Every scenario should write one record per action to
   your action log store, matching `schemas/action-log.schema.json`.
5. **For the growth/client-acquisition module specifically:** fill in
   `growth_agent.sender_identity` (real agency name + physical mailing
   address — required for cold-email compliance) and
   `growth_agent.approved_outreach_countries` (start empty; add a country
   only after confirming compliance there — see
   `docs/growth-agent/compliance-and-approval.md`) in
   `config/platforms.json` before importing anything from
   `scenarios/growth-agent/`.

## Design principles carried through from the system prompt

- **Single WhatsApp reply hub.** Instagram and Facebook DMs are routed
  through WhatsApp for replies — there is one outbound channel for customer
  support, not three.
- **Escalate, don't guess.** Anything complex, sensitive, or outside a
  pre-approved threshold goes to a human. See `docs/escalation.md`.
- **Everything is logged.** Replies, ad launches, and outreach are all
  actions with an audit trail — see `schemas/action-log.schema.json`.
- **Irreversible actions are gated.** Ad spend and bulk outreach require an
  explicit approval threshold, defined in `docs/approval-thresholds.md`.
- **No cold outreach email ever sends without per-message human approval.**
  The growth/client-acquisition module has no auto-send path at any volume
  — see `docs/growth-agent/compliance-and-approval.md`.
- **No platform scraping for contact harvesting.** Leads and emails come
  from curated imports, legitimate B2B enrichment providers, and a
  prospect's own public website/the public Meta Ad Library — never from
  automated collection against LinkedIn/Instagram/Facebook/X's ToS. See
  `docs/growth-agent/data-sourcing-policy.md`.

## Also in this repo

- [`cramble-voice-agent/`](./cramble-voice-agent/) — "Emma", an AI voice host for Cramble Restaurant (table/event bookings, menu questions). See its README.
