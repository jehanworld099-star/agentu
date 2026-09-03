# Growth agent — architecture

Maps each module in `GROWTH_AGENT_SYSTEM_PROMPT.md` to a concrete
implementation, following the same pattern as `docs/architecture.md`: a
Make.com scenario for the deterministic/orchestration parts, an LLM call
for judgment calls, and an explicit human gate before anything sends.

## Module 1 — Lead Intake & Discovery

- **Trigger:** New rows added to a Data store table (manual import / CSV)
  or a scheduled pull from a connected enrichment provider (Hunter.io/
  Apollo.io connection), per `docs/growth-agent/data-sourcing-policy.md`.
- **Flow:** `scenarios/growth-agent/lead-discovery.blueprint.json` — no
  LLM step here; this is pure data intake and validation (reject any row
  missing a sanctioned `email_source`).
- **Output:** Prospect record per `schemas/lead.schema.json` with
  `track: "ai-automation-client"`, `status: "sourced"`.

## Module 2 — Deep Business Audit & Ad Tracker

- **Flow:** `scenarios/growth-agent/business-audit.blueprint.json`.
  1. HTTP > Get (prospect's website homepage + any linked contact/about
     page).
  2. Meta Ad Library public search/API, keyed on the prospect's Facebook
     Page if known, to check current ad activity.
  3. Anthropic/Claude module running
     `prompts/growth-agent/business-audit.md` on the fetched HTML/ad data.
  4. Data store — write the resulting Client Diagnostics Brief onto the
     prospect record (`audit_brief` field), `status: "audited"`.
- **Agent step:** the LLM call is the judgment layer — classifying ad
  status and identifying copy/marketing gaps from raw page content; the
  HTTP fetch and ad-library lookup are deterministic.

## Module 3 — Solution Blueprint Design

- **Flow:** `scenarios/growth-agent/solution-blueprint.blueprint.json`.
  1. Trigger: prospect record reaches `status: "audited"`.
  2. Anthropic/Claude module running
     `prompts/growth-agent/solution-blueprint.md` against the
     `audit_brief`.
  3. Data store — write the design onto `solution_blueprint`,
     `status: "blueprint_ready"`.
- **Output:** a structured, human-readable no-code workflow outline (not a
  runnable scenario) — a human builds the real Make.com/n8n scenario from
  it once the client is signed.

## Module 4 — Humanized Cold Outreach

- **Flow:** `scenarios/growth-agent/cold-outreach.blueprint.json`.
  1. Trigger: prospect record reaches `status: "blueprint_ready"` AND its
     country is in `growth_agent.approved_outreach_countries`
     (`config/platforms.json`) — see
     `docs/growth-agent/compliance-and-approval.md`.
  2. Anthropic/Claude module running
     `prompts/growth-agent/cold-outreach.md` against `audit_brief` +
     `solution_blueprint`.
  3. Data store — write `outreach_draft` + a `hook_breakdown` (which fact
     drove which line), `status: "pending_approval"`. Scenario stops here.
  4. **Separate, human-triggered watch module**: fires only when a person
     flips the record to `status: "approved"` in the Data store/CRM UI —
     this is the "Go" command from the system prompt. Only then does the
     email-send module (SMTP/Gmail/SendGrid Make module, using the
     `growth_agent.sender_identity` configured once) actually send.
  5. Data store — log `lead_contacted` action
     (`schemas/action-log.schema.json`), `status: "contacted"`.
- **No auto-send path exists in this blueprint** — unlike
  `lead-qualification.blueprint.json`'s daily-cap auto-send, step 4 above
  has no threshold branch, only the manual approval watch.

## Module 5 — Portfolio & Social Growth

- **Flow:** `scenarios/growth-agent/portfolio-update.blueprint.json`.
  1. Trigger: prospect record reaches `status: "converted"` (a completed,
     paying engagement) AND the client has approved being referenced
     (tracked as `notes` on the record — a human confirms this before the
     scenario runs, since it is a client-facing disclosure decision, not
     an automatable one).
  2. Anthropic/Claude module running
     `prompts/growth-agent/portfolio-case-study.md` to turn the completed
     `solution_blueprint` + outcome metrics into a case-study writeup.
  3. Anthropic/Claude module running `prompts/growth-agent/social-post.md`
     to turn the same material into a social post draft — this also lands
     in `pending_approval` and needs a human "Go," same as Module 4,
     because it's still outbound content representing the agency.
  4. On approval: publish (CMS/Canva/social API module per
     `config/platforms.json`) and log the action.

## Cross-cutting

- Every record here uses the same `schemas/lead.schema.json` (extended
  with `track: "ai-automation-client"`, `audit_brief`,
  `solution_blueprint`, `email_source`, `country`) and the same action log
  as the rest of `agentu` — no parallel tracking system.
- Escalation (a prospect replies, a message bounces, a complaint) follows
  `docs/escalation.md` unchanged.
