# Growth agent scenario blueprints

Same convention as `scenarios/README.md`: each `*.blueprint.json` here is a
minimal, schema-valid Make.com blueprint with an **empty flow** — safe to
import, but you add the real app modules/connections listed below (they
depend on your Meta Business account, chosen email-enrichment provider, and
email-sending connection, none of which are known at repo-authoring time).

Validate any edits with the Make MCP `validate_blueprint_schema` tool
before importing.

## `lead-discovery.blueprint.json`

Implements: `docs/growth-agent/architecture.md` Module 1

1. Trigger — new row in a Data store table (CSV/manual import) **or**
   scheduled pull from a connected enrichment provider (Hunter.io/
   Apollo.io module), per `docs/growth-agent/data-sourcing-policy.md`.
   Do not add a social-platform scraping/login module here — see that
   policy doc for why.
2. Filter — reject any row missing a sanctioned `email_source`
   (`manual_import`, `enrichment_provider`, `prospect_website`).
3. Data store — write the prospect record (`schemas/lead.schema.json`,
   `track: "ai-automation-client"`, `status: "sourced"`).

## `business-audit.blueprint.json`

Implements: `docs/growth-agent/architecture.md` Module 2

1. Trigger — prospect record reaches `status: "sourced"`.
2. HTTP > Get Request — prospect's website homepage + contact/about page.
3. Meta Ad Library — search/API lookup for the prospect's Facebook Page
   (if known), for public ad-activity status only.
4. Anthropic/Claude module running `prompts/growth-agent/business-audit.md`.
5. Data store — write the Client Diagnostics Brief to `audit_brief`,
   `status: "audited"`.

## `solution-blueprint.blueprint.json`

Implements: `docs/growth-agent/architecture.md` Module 3

1. Trigger — prospect record reaches `status: "audited"`.
2. Anthropic/Claude module running
   `prompts/growth-agent/solution-blueprint.md`.
3. Data store — write to `solution_blueprint`, `status: "blueprint_ready"`.

## `cold-outreach.blueprint.json`

Implements: `docs/growth-agent/architecture.md` Module 4

1. Trigger — prospect reaches `status: "blueprint_ready"` **and** its
   `country` is in `growth_agent.approved_outreach_countries`
   (`config/platforms.json`).
2. Anthropic/Claude module running `prompts/growth-agent/cold-outreach.md`.
3. Data store — write `outreach_draft` + `hook_breakdown`,
   `status: "pending_approval"`. **Scenario stops here — no send module
   runs in this path.**
4. A second, separate watch module: triggers only on a human manually
   flipping the record to `status: "approved"` in the Data store/CRM UI.
   Only this path continues to an email-send module (SMTP/Gmail/SendGrid),
   using `growth_agent.sender_identity` for the required footer.
5. Data store — log `lead_contacted`
   (`schemas/action-log.schema.json`), `status: "contacted"`.

Unlike `scenarios/lead-qualification.blueprint.json`, there is no
daily-cap/auto-send branch here — see
`docs/growth-agent/compliance-and-approval.md` for why every message in
this track requires individual approval.

## `portfolio-update.blueprint.json`

Implements: `docs/growth-agent/architecture.md` Module 5

1. Trigger — prospect reaches `status: "converted"` and a human has
   confirmed (via a `notes` flag) the client approved being referenced.
2. Anthropic/Claude module running
   `prompts/growth-agent/portfolio-case-study.md`.
3. Anthropic/Claude module running `prompts/growth-agent/social-post.md`
   — output also lands as `pending_approval` (same gate as outreach).
4. On human approval: publish via a CMS/Canva/social-API module per
   `config/platforms.json`, then log the action.
