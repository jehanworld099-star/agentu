# Data sourcing policy — where prospects and emails come from

Per `GROWTH_AGENT_SYSTEM_PROMPT.md` constraint #2: this pipeline never
scrapes LinkedIn, Instagram, Facebook, X/Twitter, TikTok, or any other
platform to harvest profiles or contact details. All of those platforms'
Terms of Service prohibit automated collection of user/business data, and
several (LinkedIn especially) actively litigate against it. "The lead was
public" does not make automated extraction compliant with the site's ToS —
it's a contract violation regardless of the technique used, and it puts
both the agency's accounts and the client relationship at risk.

This is a hard boundary, not a suggestion — no scenario in
`scenarios/growth-agent/` should ever include a module that logs into or
crawls a social platform's profile/search pages.

## What's used instead

### 1. Manually curated / imported lists
The default source. The agency owner (or a researcher) compiles a list —
conference attendee lists, industry directories, referrals, a niche's
public business registry, a paid list from a reputable B2B data vendor —
and imports it as CSV/Data-store rows. This is the lowest-risk, highest-
quality source because a human already vetted fit.

### 2. Legitimate B2B email-enrichment providers
Services like Hunter.io, Apollo.io, Clearbit, or RocketReach are built for
exactly this — they find business email addresses for known companies/
people through their own compliant data pipelines (domain-pattern
inference, opt-in databases, public record aggregation with their own ToS
compliance) and are standard tooling in B2B sales. Connect one as a Make.com
app/connection; do not attempt to replicate their function by scraping
social profiles yourself. Store only the provider name in
`config/platforms.json` (non-secret); credentials live in Make's connection
store.

### 3. The prospect's own public website
Fetching a business's own public website (contact page, footer, About page)
to find a general or role-based inbox (`hello@`, `info@`, `partnerships@`)
is standard, low-risk, and not covered by any social-platform ToS — it's
their own site, meant to be read by visitors and search engines. This is
what `scenarios/growth-agent/business-audit.blueprint.json` does as a
byproduct of the audit fetch.

### 4. Meta Ad Library (for ad status only, not contacts)
Meta publishes an Ad Library specifically so ads run on Facebook/Instagram
are publicly auditable — this is Meta's own transparency tool, accessed via
its public library/API, not a scrape of a Page's private data. Use it only
to answer "are they currently running ads, and what do the ads look like,"
never to extract personal contact information.

## Email quality bar before a prospect enters Module 4

- Prefer a role-based or company-domain email (`name@company.com`,
  `hello@company.com`) over a personal/free-provider address
  (`@gmail.com`, `@yahoo.com`) scraped or guessed from a personal profile.
  Personal-address cold email is both lower-quality and higher compliance
  risk (more likely to be a private individual, not a business decision
  maker acting in that capacity).
- Every prospect record must set `email_source` to one of the sanctioned
  values in `schemas/lead.schema.json` (`manual_import`,
  `enrichment_provider`, `prospect_website`). A record with no valid
  `email_source` does not proceed past Module 1.
- If no compliant email can be found for a prospect, leave it as
  `sourced` with no outreach — do not fall back to guessing or scraping to
  fill the gap.
