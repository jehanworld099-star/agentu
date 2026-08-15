# Approval Thresholds

Per the system prompt's Operating Principles: *"Never take irreversible
actions (spending ad budget, sending outreach at scale) without a defined
approval threshold."*

This document is the definition. Edit the values for your business before
enabling any live scenario — the defaults below are conservative starting
points, not recommendations.

## Ad spend

| Action | Threshold | Below threshold | At/above threshold |
|---|---|---|---|
| New campaign launch | Any daily budget > **$20/day** or lifetime budget > **$200** | Agent may launch automatically, logged | Agent produces a draft brief only; requires explicit human approval before launch |
| Budget increase on a live campaign | Increase > **20%** of current budget | Auto-adjust, logged | Requires approval |
| New audience/targeting change | Always | — | Requires approval (targeting mistakes are costly and slow to detect) |

## Outreach (copywriting leads + agent-service leads)

| Action | Threshold | Below threshold | At/above threshold |
|---|---|---|---|
| Outreach messages sent per day (per track) | **10/day** | Agent may send automatically, logged | Batch queued for human review/approval |
| First-time cold outreach to a new prospect | Always | — | Draft only; require approval for the first message in any new thread |
| Follow-up in an existing thread the prospect replied to | Always | — | Requires escalation (this is now a live conversation — see `escalation.md`) |

## Customer support (WhatsApp reply hub)

| Action | Threshold | Below threshold | At/above threshold |
|---|---|---|---|
| Auto-reply to routine question (pricing/availability/catalog) | Always allowed | Send immediately, logged | N/A |
| Anything not confidently classified as routine | Always | — | Escalate to human (see `escalation.md`); do not guess |

## How to change these

These are configuration, not code — update the numbers here, then mirror
them into the corresponding Make.com scenario's router/filter modules
(`scenarios/*.blueprint.json`) so the gate is enforced at execution time, not
just documented.
