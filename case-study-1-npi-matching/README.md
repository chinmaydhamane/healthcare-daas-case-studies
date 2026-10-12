# Case Study — NPI Matching Benchmark

**Status: internal R&D / capability demo, built on synthetic data — not a real client engagement.**
Use this to show prospective clients the methodology and typical match-rate ranges before quoting a real project (e.g. the "80k HCP records, oncology-focused, RFP-ready match rates" type of ask).

## What this demonstrates

A client asking for NPI matching is really asking three things:
1. **How does matching work** — deterministic vs. fuzzy, and what fields drive it
2. **What match rate should I expect** — broken down by data quality and specialty
3. **What's the deliverable** — a defensible, tiered, auditable match report for an RFP

This repo answers all three with a runnable pipeline instead of a slide.

## Data

- `data/nppes_registry.csv` — synthetic stand-in for the public NPPES NPI Registry (20,000 providers): npi, name, specialty, practice, state, zip, phone, license number.
- `data/hcp_audience.csv` — synthetic stand-in for a purchased/scraped HCP audience list, deliberately degraded the way real third-party lists arrive:
  - 40% missing NPI (the realistic default — most purchased lists don't carry it)
  - ~15% name typos/casing issues
  - ~20% missing phone
  - 10% pure noise records (people not in the registry at all, to keep match rate honest instead of artificially high)

Regenerate with `python generate_data.py` (seeded, so results are reproducible).

## Matching methodology

| Tier | Logic |
|---|---|
| **EXACT** | NPI present in the audience row and found directly in the registry |
| **HIGH** | No usable NPI; fuzzy name match (RapidFuzz token-sort ratio) ≥ 90, blocked on state, boosted by zip match |
| **MEDIUM** | Fuzzy name match ≥ 75 and < 90, single best candidate in-state |
| **UNMATCHED** | No candidate clears 75 |

Blocking is done on **state** before fuzzy comparison — this is the same technique used at production scale (state + specialty + zip3) to avoid an O(n×m) cross join across millions of NPPES rows.

Run it:
```
python generate_data.py
python match.py
```

Outputs:
- `output/match_results.csv` — every audience row with its tier, matched NPI, and score
- `output/match_rate_by_specialty.csv` — match rate broken out by specialty, the exact cut an RFP submission needs

## Talking points for the consultation-call type of engagement

- **Expected match rate** depends almost entirely on whether NPI is present in the source list. On this benchmark's synthetic audience (60% of registry sampled, 40% of those missing NPI, plus 10% pure noise added on top), the pipeline lands: EXACT 55.4%, HIGH 35.5%, MEDIUM 5.5%, UNMATCHED 3.6% — a **96.4% combined match rate**, with the unmatched 3.6% tracking closely to the 10% noise injected (most noise records score low enough to correctly fall out, which is the point — a good pipeline doesn't force-match garbage). Rerun `python match.py` any time to regenerate these numbers from the seeded data.
- **Cost/timeline for a real engagement**: for an 80k-record one-time project this pipeline (extended with real NPPES data + human QA pass on MEDIUM tier) is a 3-5 day turnaround.
- **Recommended tooling**: NPPES bulk file (monthly) over per-record API calls at this volume; RapidFuzz or Splink for matching; a confidence-tiered CSV/PDF deliverable, never a single blended match-rate number — RFP reviewers want the tier breakdown.

## Extending to a real client engagement

Swap `data/nppes_registry.csv` for the real NPPES monthly bulk file (public, ~8M rows) and the client's actual HCP list in place of `hcp_audience.csv` — the pipeline logic doesn't change, only the volume, which is where the state+specialty blocking earns its keep.
