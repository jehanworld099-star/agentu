# Prompt: Humanized cold outreach draft

Used by: `scenarios/growth-agent/cold-outreach.blueprint.json` (draft stage
only — sending is gated, see
`docs/growth-agent/compliance-and-approval.md`; there is no auto-send path
for this module, unlike `prompts/outreach-copywriting.md`)
Implements: `GROWTH_AGENT_SYSTEM_PROMPT.md` Module 4

## Inputs

- `prospect`: qualified prospect record, including `audit_brief` and
  `solution_blueprint`.
- `sender_identity`: agency name, physical mailing address, unsubscribe
  instructions (from `config/platforms.json` →
  `growth_agent.sender_identity` — see
  `docs/growth-agent/compliance-and-approval.md`).

## Banned phrases (hard filter — regenerate if any appear)

"in today's digital landscape", "tapestry", "revolutionize", "delve",
"unlock your potential", "game-changer", "take it to the next level",
"synergy", "leverage" (as a verb), "in the fast-paced world of", "seamless
solution", "elevate your brand", "unleash", "empower", any sentence
starting with "I hope this email finds you well" or "I wanted to reach
out."

## Instructions

```
Draft a short, specific cold outreach email pitching AI automation help to
{{prospect.name}}, using the AIDA or PAS framework.

Diagnostics brief:
{{audit_brief}}

Solution blueprint summary:
{{solution_blueprint.summary}}

Sender: {{sender_identity}}

Rules:
- Open with one concrete, specific observation from audit_brief — never a
  generic "I noticed you could use help with marketing." The reader should
  recognize their own business in the first line.
- State the cost of the gap in plain terms (lost sales, wasted ad spend,
  visitors who never come back) before pitching anything — value framing
  before the ask.
- Reference the fix at a conceptual level only (from
  solution_blueprint.summary) — do not give away the full technical
  blueprint for free; that's the paid deliverable.
- One clear, low-friction call to action (e.g. "want the 2-minute version
  of what this would look like for you?").
- Under 120 words. No exclamation points. No emojis. No banned phrases
  above.
- Must end with the sender's real identity, physical address, and a plain
  reply-to-opt-out line, verbatim from sender_identity — do not paraphrase
  or drop this even if it makes the email longer or "less punchy."

Output as JSON:
{
  "subject_line": "<specific, honest — no clickbait/misleading claims>",
  "body": "<the full email, ready to send as-is, including the
    sender-identity footer>",
  "hook_breakdown": [
    {"line": "<line from body>", "grounded_in": "<specific fact from
      audit_brief that justifies this line>"}
  ]
}
```

## Notes

- `hook_breakdown` is what gets shown to the human alongside the draft per
  the Intercept Rule — it's how the owner verifies the personalization is
  real and not a templated-looking guess before approving.
- If `audit_brief.overall_fit` is `"weak"`, do not draft — return a note
  explaining why this prospect shouldn't be outreached yet instead of
  forcing a low-quality pitch.
