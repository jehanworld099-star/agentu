# Architecture

This maps each responsibility in `SYSTEM_PROMPT.md` to a concrete
implementation approach: which platform APIs are involved, how Make.com
orchestrates them, and where the agent (an LLM call) makes a decision versus
where it's a deterministic automation step.

## 1. Multi-Platform Management

- **Data sources:** Facebook Graph API (Page insights), Instagram Graph API
  (media + insights), YouTube Data/Analytics API.
- **Flow:** A scheduled Make.com scenario (`scenarios/platform-health-check.blueprint.json`)
  polls each connected account daily, pulls posting cadence and engagement
  metrics, and writes a snapshot row per account.
- **Agent step:** An LLM call compares each account's trailing 7/30-day
  metrics against its own history (not a global benchmark) and flags
  accounts that are inactive (no post in N days, configurable) or
  underperforming (engagement rate dropped beyond a threshold).
- **Output:** A flagged-accounts list feeds into the growth report (§3) and
  can optionally trigger a human notification.

## 2. Unified Customer Support (WhatsApp Reply Hub)

- **Inbound:** Facebook Messenger webhook + Instagram Messaging webhook,
  both routed into one Make.com scenario
  (`scenarios/inbound-message-router.blueprint.json`).
- **Normalization:** Each inbound message is normalized into a common
  shape `{platform, customer_id, thread_id, text, timestamp}` regardless of
  origin.
- **Agent step:** The LLM classifies the message as: routine (pricing,
  availability, catalog question — answer from a knowledge base / FAQ
  prompt, see `prompts/customer-support-reply.md`) or complex/sensitive
  (complaint, refund, legal, anything the FAQ prompt has no grounded answer
  for — escalate per `docs/escalation.md`).
- **Outbound:** All replies — regardless of which platform the customer
  originally used — are sent via the WhatsApp Business Cloud API, per the
  system prompt's "Unified Customer Support" requirement. This means the
  scenario must resolve/maintain a mapping from `{platform, customer_id}` to
  a WhatsApp-reachable number/thread; see `schemas/lead.schema.json`-adjacent
  contact record for this mapping (tracked as part of the CRM state, not
  duplicated here).
- **Latency target:** This scenario runs on the inbound webhook trigger
  (not polling) to keep response time as close to real-time as possible, per
  the Operating Principles.

## 3. Growth & Strategy Suggestions

- **Flow:** A weekly/monthly scheduled scenario
  (`scenarios/growth-report.blueprint.json`) aggregates the metrics
  snapshots from §1 across FB/IG/YouTube.
- **Agent step:** LLM call using `prompts/growth-report.md` turns the raw
  metrics into: best posting times, content format trends, hashtag/keyword
  opportunities, and engagement tactics, summarized as a report.
- **Output:** Report is logged as an action (`report_generated`) and
  delivered to the human owner (email/Slack/WhatsApp per configuration).

## 4. Copywriting Client Acquisition

- **Sourcing:** Prospects come from a configured list of target accounts or
  a discovery scenario that samples public Pages in a niche/geo.
- **Agent step:** LLM scores each prospect using `prompts/lead-qualification-copywriting.md`
  against business size, current content quality, and platform activity
  signals, then drafts outreach with `prompts/outreach-copywriting.md`.
- **Gate:** Drafts are queued, not sent, until they clear the bulk-outreach
  approval threshold in `docs/approval-thresholds.md`.
- **Tracking:** Each prospect is a record per `schemas/lead.schema.json`
  with `track` set to `copywriting`.

## 5. Agent Self-Promotion & Sales

- Same pipeline as §4, but qualifying for "would benefit from this
  automation agent" rather than copywriting, using
  `prompts/lead-qualification-agent-service.md` and
  `prompts/outreach-agent-service.md`.
- **Tracking:** Same `schemas/lead.schema.json`, `track` set to
  `agent-service`, with `status` moving through
  `contacted -> interested -> converted`.

## 6. Facebook Ads Management

- **Flow:** `scenarios/ad-campaign-launch.blueprint.json` uses Make.com's
  native Facebook Ads modules to create a campaign, ad set (audience +
  budget), and ad (creative) from a structured brief.
- **Agent step:** LLM turns a business goal (e.g. "more bookings this
  week", target budget) into the structured brief via
  `prompts/ad-campaign-brief.md`: audience definition, budget, and creative
  copy/asset selection.
- **Gate:** Campaign launch (spending money) is the clearest "irreversible
  action" in the system prompt — it requires explicit approval above the
  threshold in `docs/approval-thresholds.md` before the Make.com scenario is
  allowed to actually create the campaign (vs. producing a draft brief for
  human review).
- **Monitoring:** A separate scheduled scenario polls ad performance and
  feeds cost-per-result/conversion data back to the LLM for
  targeting/budget adjustment suggestions, which are themselves gated the
  same way as the initial launch.

## Cross-cutting: logging

Every scenario above writes one record per action to the action log
(`schemas/action-log.schema.json`) — this is what "Log every action taken
(reply sent, ad launched, lead contacted) for review" means operationally.
