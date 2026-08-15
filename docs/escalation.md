# Escalation

Per the system prompt: *"When uncertain about a customer request or a
business decision, escalate to a human rather than guessing."*

## Always escalate

- Complaints, refund/dispute requests, anything with legal or safety
  implications.
- Any message the FAQ/knowledge-base prompt (`prompts/customer-support-reply.md`)
  cannot answer with a grounded, on-brand response.
- A prospect (copywriting or agent-service track) replying to outreach —
  once a human is in a live back-and-forth, the agent stops drafting
  autonomous follow-ups and hands the thread to a human, optionally
  drafting a suggested reply for them to approve/edit.
- Any action at or above a threshold in `docs/approval-thresholds.md`.
- Any account showing signs of being compromised, impersonated, or
  targeted by coordinated abuse.

## How escalation works

1. The triggering scenario writes an `escalation_needed` action log entry
   (see `schemas/action-log.schema.json`) with the reason and full context
   (thread, platform, customer id).
2. The scenario notifies the human owner through the configured channel
   (WhatsApp/email/Slack — set in `config/platforms.json`).
3. The agent does **not** send a reply or take the gated action until a
   human responds. If the customer-facing channel requires *some*
   acknowledgment to hit the real-time response target, send only a
   neutral holding message (e.g. "Thanks for reaching out — one of our team
   will follow up shortly") — never a substantive answer to an escalated
   question.

## What escalation is not

Routine questions with a clear, confident answer in the FAQ/knowledge base
are handled automatically — escalation exists for genuine uncertainty and
irreversible/gated actions, not as a blanket "ask a human first" for
everything.
