# Case Study — Multi-Source Lead-List Enrichment Workflow

**Status: internal R&D / capability demo, built on synthetic data — not a real client engagement.**
Mirrors the "healthcare data mining specialist" brief: mine provider info and complete accurate data entry across email, phone, practice name, and LinkedIn, validated against CMS/NPPES, across multiple specialties.

## Legal/ethical note (read before pitching this)

This demo does **no actual scraping** — it generates synthetic data with realistic *shapes* (coverage gaps, duplication, conflicting values across sources) so the enrichment logic can be shown without touching any real website. In a real engagement:
- Only collect from sources whose Terms of Service and `robots.txt` permit it, or from public government data (NPPES itself is fully public).
- LinkedIn's ToS specifically prohibits automated scraping — for that class of source, the realistic approach is manual/human-in-the-loop lookup, a licensed data provider, or LinkedIn's own Sales Navigator/API exports, not a bot.
- Treat this as the reason the service is valuable: knowing *which* sources are safe to automate and which require a different approach is exactly the judgment a client is paying for, not something they get from a generic script.

## Why a single scrape is never enough

The real problem in this space isn't "get provider emails" — it's that **no single source has complete data**, and each source has systematically different gaps:

| Source (synthetic) | Strong on | Weak on |
|---|---|---|
| Public provider directory | phone, practice name | email, LinkedIn (almost never) |
| Practice websites | email | phone (~50% missing), includes off-registry noise (retired/locum providers) |
| Professional-profile-style source | LinkedIn URL, practice name | phone/email (almost never), some name-spelling drift |

A usable lead list requires **merging across sources per provider**, not just stacking them — and validating every merged identity against NPPES so the client isn't paying for contacts who don't exist or can't be verified.

## What this demonstrates

- `generate_sources.py` — synthetic NPPES registry (3,000 providers) plus three source files that mimic the coverage pattern above, including realistic duplication and ~8% off-registry noise in the practice-site source.
- `enrich.py`:
  1. Fuzzy-matches every scraped row to the NPPES registry (same blocking + RapidFuzz approach as [Case Study 1](../npi-match-demo/)) to get a canonical NPI — this is the validation step the brief specifically asks for.
  2. Groups all source rows resolving to the same NPI and merges fields, preferring the source with the best known coverage for each field (e.g. email from practice sites, phone from the directory site, LinkedIn from the profile-style source), falling back to whatever's available.
  3. Scores each merged lead for completeness (name, practice, phone, email, LinkedIn, state) and separately flags rows that couldn't be validated against NPPES at all.

Run it:
```
python generate_sources.py
python enrich.py
```

## Observed results on this run

- 4,920 raw rows scraped across 3 sources → 4,771 validated against NPPES, 149 flagged and excluded as unverifiable/off-registry
- Merged down to **2,724 unique verified providers**
- **79.5% average field completeness** (of 6 target fields) after merging — up from what any single source alone would provide (each source individually covers at most 2-3 of the 6 fields well)
- 497 leads fully complete (6/6 fields)

Outputs:
- `output/enriched_leads.csv` — the deliverable lead list, sorted by completeness
- `output/unvalidated_flagged.csv` — excluded rows, kept separately for transparency/audit rather than silently dropped

## Talking points for this type of engagement

- **"Multi-specialty support"** (Cardiology, GI, Primary Care in the brief) is just a filter on the merged, validated table — the pipeline doesn't change per specialty, only the client-facing cut of the output does.
- **Data integrity for sensitive provider data**: every lead is traceable to which source(s) it came from (`sources_seen` column) and whether it was NPPES-validated — this is the "detail-oriented, comfortable handling sensitive provider data with accuracy and consistency" requirement made concrete and auditable, not just a promise.
- **Why merge beats single-source scraping**: quantify it like the numbers above — a client evaluating "should I pay for one big scrape or a merge-and-validate service" should see that merge is what actually gets completeness above 50-60%.
- **Pricing angle**: this is naturally a retainer service (new practices/providers appear monthly, contact info goes stale) rather than a one-time deliverable — ties directly into [Case Study 2](../npi-cdc-demo/)'s monthly refresh pipeline.

## Relationship to the other case studies

This is the front-of-pipeline stage: **scrape/source → merge & validate (this repo) → maintain history ([Case Study 2](../npi-cdc-demo/)) → match against a client's own audience list ([Case Study 1](../npi-match-demo/))**. Together the three demonstrate the full DaaS retainer, not just a one-off script.
