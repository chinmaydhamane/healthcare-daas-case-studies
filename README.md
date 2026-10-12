# Healthcare Data-as-a-Service — Capability Case Studies

**Status: internal R&D / capability demos built on synthetic data — not real client engagements.**
These are runnable proof-of-methodology pipelines built to demonstrate a productized
**NPI Matching & HCP Data Enrichment as a Service** offering for healthcare, pharma, and
life-sciences clients — the kind of work seen in briefs asking for NPI matching, HCP data
validation, and healthcare lead-list enrichment against CMS/NPPES data.

No real scraping or third-party data was used anywhere in this repo — every dataset is
synthetically generated to have realistic *shapes* (coverage gaps, duplication, typos, noise)
so the pipeline logic can be demonstrated and benchmarked honestly, without any ToS or privacy
concerns.

## The three case studies

| # | Case study | What it proves | Folder |
|---|---|---|---|
| 1 | **NPI Matching Benchmark** | Deterministic-first, fuzzy-fallback matching of a messy HCP audience list against the NPI registry, with confidence-tiered results (EXACT/HIGH/MEDIUM/UNMATCHED) and match rates by specialty — the exact deliverable an RFP submission needs. | [`case-study-1-npi-matching/`](case-study-1-npi-matching/) |
| 2 | **Monthly NPPES Change-Data-Capture (SCD2)** | A warehouse that tracks provider changes month over month (new/changed/deactivated) instead of silently overwriting data — the mechanism behind an "always current" retainer service. | [`case-study-2-nppes-cdc/`](case-study-2-nppes-cdc/) |
| 3 | **Multi-Source Lead-List Enrichment** | Merging multiple partial sources (directory sites, practice websites, profile-style sources) into one validated, NPPES-cross-checked lead list with a completeness score. | [`case-study-3-lead-enrichment/`](case-study-3-lead-enrichment/) |

Each folder has its own README with the full methodology, talking points for client
conversations, and instructions to re-run it locally (`python generate_*.py` then the pipeline
script).

## All-in-one notebook

[`notebook/healthcare_daas_case_studies.ipynb`](notebook/healthcare_daas_case_studies.ipynb)
walks through all three case studies end-to-end in one place — markdown explanations next to
the code that generates the data, runs each pipeline, and shows the results — already executed,
so every output is visible without re-running anything.

## How these three fit together

```
Scrape/source (Case 3) → Merge & validate (Case 3) → Maintain history, SCD2 (Case 2)
    → Match against a client's own audience list (Case 1) → RFP-ready / retainer deliverable
```

## Why this is still a real service in the age of AI-generated scripts

The core matching/fuzzy-logic script is commodity now — AI can draft one in a single prompt.
What a client is actually paying for is the layer that doesn't come from a prompt:

- **Judgment on match confidence** — owning and defending the tier thresholds and methodology in front of legal/compliance reviewers, not just producing a number.
- **Operational reliability at volume** — running this monthly against real, messy, multi-million-row data, with monitoring and a response plan when a source schema changes.
- **Compliance/provenance awareness** — knowing what's public (NPPES) vs. what needs consent tracking (scraped contact data), and which sources can't be automated at all (e.g. LinkedIn's ToS prohibits scraping).
- **Ongoing accountability** — a named person responsible for the numbers every month, not a one-off script someone ran once.

## Running locally

Each case study folder is self-contained with its own `requirements.txt`:

```bash
cd case-study-1-npi-matching
pip install -r requirements.txt
python generate_data.py
python match.py
```

Same pattern for case studies 2 and 3. The notebook installs nothing on its own — run its first
cell's imports after `pip install pandas rapidfuzz faker`.
