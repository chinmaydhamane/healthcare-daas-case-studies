# Case Study — Monthly NPPES Change-Data-Capture / SCD2 Pipeline

**Status: internal R&D / capability demo, built on synthetic data — not a real client engagement.**
This is the proof-of-mechanism behind the retainer pitch: *"we deliver a clean, query-ready, always-current HCP warehouse every month"* — not just a one-time match, but an ongoing service with real change history.

## Why this matters to a client

NPPES republishes its full registry monthly. Providers get added, deactivated, change specialty/taxonomy, move practices, or update contact info constantly. A client who just re-downloads and overwrites their table every month:
- loses the ability to answer "what did this provider's info look like last quarter"
- can't produce a clean "here's what changed" report for stakeholders
- risks silently losing deactivated NPIs instead of flagging them

This pipeline solves that with a standard data-warehousing pattern (**SCD Type 2**) applied specifically to NPPES's monthly cadence.

## What this demonstrates

- `generate_snapshots.py` — builds two synthetic monthly NPPES-like snapshots (August → September) with realistic month-over-month churn: ~2% new providers, ~1% deactivations, ~4% address/practice/phone changes, ~1.5% specialty/taxonomy changes.
- `load_scd2.py` — loads both snapshots into a `hcp_master` table (SQLite for the demo; the same logic applies unchanged in Snowflake/BigQuery/Postgres) using SCD2: every change expires the old row (`is_current = 0`, `end_date` set) and inserts a new current row (`effective_date` set, `change_reason` tagged).
- `report.py` — produces the actual client deliverable: a monthly change report (new / changed / deactivated providers) that can be handed off or piped into a dashboard.

Run it:
```
python generate_snapshots.py
python load_scd2.py
python report.py
```

## Observed results on this run

Loading September's snapshot against August's baseline (5,000 providers):

| Change type | Count |
|---|---|
| New providers | 100 |
| Changed (specialty/practice/zip/phone) | 272 |
| Deactivated | 50 |
| Unchanged | 4,678 |

Every changed record retains full history — e.g. a provider's practice name, zip, and phone before and after the change are both queryable, each tagged with its own effective/end date and the specific fields that changed (`CHANGED:practice_name,zip,phone`).

## Talking points for the retainer pitch

- **What "always current" actually requires**: not just re-loading data, but a schema (SCD2) that preserves history instead of overwriting it — this is the difference between a one-time export and a managed pipeline.
- **What clients get monthly**: a change report (this repo's `output/september_change_report.csv`) broken into new/changed/deactivated, plus a point-in-time-queryable warehouse table for ad hoc "what did we know about provider X on date Y" questions — useful for compliance/audit trails in pharma and life-sciences engagements.
- **Cost/effort model**: the marginal cost of running this monthly is low once built (this is the scalability argument for MRR pricing — same pipeline template reused per client, only the source list and blocking keys change).
- **Extending to production**: swap SQLite for the client's warehouse (Snowflake/BigQuery/Postgres — same SQL/DDL pattern), swap the synthetic CSVs for the real NPPES monthly bulk file, and schedule the load with Airflow/dbt Cloud/cron depending on the client's stack.

## Relationship to Case Study 1

This pipeline produces the **current, deduplicated `hcp_master` table** that Case Study 1's [NPI Matching Benchmark](../npi-match-demo/) matches an incoming HCP audience list against — together they cover the full lifecycle: ingest → maintain history → match/enrich → deliver.
