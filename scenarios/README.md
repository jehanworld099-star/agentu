# Scenario blueprints

Each `*.blueprint.json` file here is a minimal, schema-valid Make.com
scenario blueprint — safe to import into Make.com as a starting canvas. They
intentionally ship with an **empty flow**: none of them reference real
Make.com app modules or connections, because those depend on your specific
Meta Business/YouTube/WhatsApp accounts, which aren't known at repo-authoring
time. Fabricating plausible-looking module references here would import as
broken (Make validates module existence/config at creation time, not just
blueprint structure) — so instead, each stub below lists exactly which
modules to add once imported.

Validate any blueprint you edit with the Make MCP `validate_blueprint_schema`
tool (or Make.com's own import validation) before importing.

## `platform-health-check.blueprint.json`

Implements: `docs/architecture.md` §1 (Multi-Platform Management)

1. Scheduler trigger — daily.
2. Facebook Pages > Get Page Insights (per configured Page ID).
3. Instagram > Get Media Insights (per configured Page ID).
4. YouTube > Get Channel/Video Analytics (per configured Channel ID).
5. Aggregator — combine into one snapshot record.
6. HTTP/Data store — write the snapshot (matches the metrics shape consumed
   by `growth-report.blueprint.json`).
7. Anthropic/Claude module (or HTTP call to your LLM endpoint) using the
   flagging logic in `docs/architecture.md` §1 to mark accounts inactive/
   underperforming.

## `inbound-message-router.blueprint.json`

Implements: `docs/architecture.md` §2 (Unified Customer Support)

1. Facebook Messenger > Watch Messages (webhook, instant trigger).
2. Instagram > Watch Messages (webhook, instant trigger).
3. Router — merge both trigger paths into one downstream flow, normalizing
   to `{platform, customer_id, thread_id, text, timestamp}`.
4. Anthropic/Claude module running `prompts/customer-support-reply.md`.
5. Filter — branch on `classification` (`ROUTINE` vs `ESCALATE`).
6. WhatsApp Business Cloud API > Send Message — for both branches (routine
   answer, or holding message), per the "reply via WhatsApp regardless of
   origin platform" requirement.
7. On `ESCALATE`: also notify the human owner and write an
   `escalation_needed` action log entry.
8. Data store — write an action log entry for every reply sent (see
   `schemas/action-log.schema.json`).

## `growth-report.blueprint.json`

Implements: `docs/architecture.md` §3 (Growth & Strategy Suggestions)

1. Scheduler trigger — weekly/monthly (per `config/platforms.json`
   `reporting.cadence`).
2. Data store > Search Records — pull the period's snapshots written by
   `platform-health-check.blueprint.json`.
3. Anthropic/Claude module running `prompts/growth-report.md`.
4. Delivery module (Email/Slack/WhatsApp, per
   `config/platforms.json.business.human_owner_notification_channel`) —
   send the report.
5. Data store — log `report_generated` action.

## `lead-qualification.blueprint.json`

Implements: `docs/architecture.md` §4 and §5 (Copywriting leads +
Agent-service leads)

1. Trigger — new prospect record added to the source list/discovery
   scenario, tagged with `track` = `copywriting` or `agent-service`.
2. Router on `track`.
3. Anthropic/Claude module running the matching qualification prompt
   (`prompts/lead-qualification-copywriting.md` or
   `prompts/lead-qualification-agent-service.md`).
4. Filter — only `qualified: true` prospects continue.
5. Anthropic/Claude module running the matching outreach draft prompt.
6. Data store — write/update the lead record (`schemas/lead.schema.json`),
   status `pending_approval`.
7. Batch/aggregate against the daily outreach cap in
   `docs/approval-thresholds.md`; only records under the cap and past
   human approval move to `contacted` and actually send (Messenger/
   Instagram DM/email module, per prospect's available contact channel).

## `ad-campaign-launch.blueprint.json`

Implements: `docs/architecture.md` §6 (Facebook Ads Management)

1. Trigger — business goal submitted (form/webhook/manual run).
2. Anthropic/Claude module running `prompts/ad-campaign-brief.md`.
3. Filter — budget from the brief vs. the thresholds in
   `docs/approval-thresholds.md`.
   - Under threshold: continue directly to launch.
   - At/above threshold: write the brief as `pending_approval` and notify
     the human owner; only continue on explicit approval (e.g. a
     Data-store status flip picked up by a follow-up watch module).
4. Facebook Ads > Create Campaign / Create Ad Set / Create Ad (Make's
   native Facebook & Instagram Ads modules), using the approved brief.
5. Data store — log `ad_campaign_launched`.
6. Separate scheduled scenario (clone of this one's back half): poll ad
   performance, feed cost-per-result back into another
   `prompts/ad-campaign-brief.md`-style adjustment call, gated the same
   way for any budget change.
