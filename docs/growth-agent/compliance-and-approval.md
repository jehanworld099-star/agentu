# Compliance and approval — cold outreach

This overrides the general outreach row in `docs/approval-thresholds.md`
for the growth-agent pipeline specifically.

## Approval: every message, every time

`docs/approval-thresholds.md` allows up to 10 auto-sent outreach messages
per day, per track, before batching for review. **That allowance does not
apply here.** Per `GROWTH_AGENT_SYSTEM_PROMPT.md`'s Intercept Rule, every
single message drafted by `prompts/growth-agent/cold-outreach.md` is
written to the lead record with `status: pending_approval` and a human
must flip it to `approved` individually before the send module runs. There
is no batch-approve-all step and no volume-based auto-send path for this
module. If a future scenario needs bulk sending, that requires a separate,
explicit decision by the agency owner to change this document — not a
default.

## Why this matters more for international outreach

Cold email law is not one rule — it changes by the recipient's country, and
mistakes here range from fines to platform/ESP suspension:

| Regime | Applies to | Key requirements |
|---|---|---|
| CAN-SPAM (US) | Commercial email to US recipients | Accurate header/from, no deceptive subject, physical postal address, clear/functioning opt-out honored within 10 business days, must self-identify as an ad if applicable |
| UK GDPR + PECR | Email to UK-based individuals/businesses | B2B "legitimate interest" cold email is narrower than commonly assumed — must be relevant to the recipient's role, easy opt-out, and honest about data source |
| EU GDPR + national e-privacy rules | Email to EU-based recipients | Varies by member state — some (e.g. Germany) are stricter than others about unsolicited B2B email even with legitimate interest; do not treat "GDPR-compliant" as one uniform bar |
| CASL (Canada) | Email to Canada-based recipients | Generally requires *consent* (express or a narrow implied-consent exception) before sending, not just an opt-out — cold B2B email without a qualifying prior relationship is high-risk here |
| Spam Act 2003 (Australia) | Email to Australia-based recipients | Consent, identify sender, functional unsubscribe |

This table is a starting orientation, not legal advice — verify current
requirements for your actual target countries before scaling outreach, and
get a lawyer's sign-off before treating any jurisdiction as cleared for
volume.

## Baseline rules applied to every draft, regardless of destination country

1. **B2B, role-based targeting only.** Address the business/decision-maker
   in their business capacity, at a business or role-based address — never
   a personal account address obtained outside the sanctioned sources in
   `docs/growth-agent/data-sourcing-policy.md`.
2. **Real sender identity.** The agency's real name and a physical mailing
   address appear in every message (configured once in
   `config/platforms.json` → `growth_agent.sender_identity`, not
   hardcoded per-message).
3. **Working, honored opt-out.** Every message includes a functioning
   unsubscribe/reply-to-stop mechanism. An opt-out is enforced permanently
   — a prospect who opts out is marked `not_interested` and is
   excluded from all future sourcing, not just the current campaign.
4. **No purchased consumer lists.** Only the sources in
   `docs/growth-agent/data-sourcing-policy.md`.
5. **Per-country gate.** `config/platforms.json` →
   `growth_agent.approved_outreach_countries` is an explicit allow-list.
   A prospect whose country isn't on that list is qualified/audited
   (Modules 1-3) but Module 4 refuses to draft outreach for it until the
   owner adds that country after confirming compliance for it.
6. **One escalation path for replies.** The moment a prospect replies, this
   pipeline stops drafting autonomous follow-ups and hands the thread to a
   human, per `docs/escalation.md` — identical to the rule already in place
   for the copywriting/agent-service tracks.
