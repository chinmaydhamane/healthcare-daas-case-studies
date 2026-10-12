"""
Lead-list enrichment pipeline: merges multiple scraped/purchased sources
into one record per provider, cross-validates against the NPPES registry,
and fills in the fields the "healthcare data mining" brief asks for
(email, phone, practice name, LinkedIn) from whichever source has them.

Steps:
  1. Load each source, blocked on (state) then fuzzy-matched by name to the
     NPPES registry to attach a canonical npi + specialty (same technique
     as Case Study 1's matching pipeline).
  2. Group all source rows that resolved to the same NPI into one lead
     record, merging fields — preferring the source with best known
     coverage for that field (email from practice sites, phone from
     directory sites, LinkedIn from the professional-profile source) but
     falling back to whatever is present.
  3. Score each merged lead on completeness (name, practice, phone, email,
     linkedin, state = 6 fields) and flag NPPES-validated vs. unvalidated.

Usage:
    python enrich.py
"""
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

DATA_DIR = Path(__file__).parent / "data"
OUT_DIR = Path(__file__).parent / "output"
OUT_DIR.mkdir(exist_ok=True)

FIELD_PRIORITY = {
    "phone": ["directory_site", "practice_site", "linkedin_style"],
    "email": ["practice_site", "directory_site", "linkedin_style"],
    "linkedin_url": ["linkedin_style", "practice_site", "directory_site"],
    "practice_name": ["directory_site", "linkedin_style", "practice_site"],
}

MATCH_THRESHOLD = 85


def load_registry():
    return pd.read_csv(DATA_DIR / "nppes_registry.csv", dtype=str).fillna("")


def load_sources():
    names = ["source_directory_site.csv", "source_practice_sites.csv", "source_linkedin_style.csv"]
    frames = [pd.read_csv(DATA_DIR / n, dtype=str).fillna("") for n in names]
    return pd.concat(frames, ignore_index=True)


def attach_npi(sources, registry):
    """Fuzzy-match each scraped row to the NPPES registry, blocked on state."""
    reg_by_state = {s: g.reset_index(drop=True) for s, g in registry.groupby("state")}
    name_choices = {
        s: (g["first_name"] + " " + g["last_name"]).str.lower().tolist()
        for s, g in reg_by_state.items()
    }

    npis, specialties, validated = [], [], []
    for _, row in sources.iterrows():
        candidates = reg_by_state.get(row["state"])
        full_name = f"{row['first_name']} {row['last_name']}".lower()
        if candidates is None or candidates.empty:
            npis.append(""); specialties.append(""); validated.append(False)
            continue
        match = process.extractOne(full_name, name_choices[row["state"]], scorer=fuzz.token_sort_ratio)
        if match and match[1] >= MATCH_THRESHOLD:
            cand = candidates.iloc[match[2]]
            npis.append(cand["npi"]); specialties.append(cand["specialty"]); validated.append(True)
        else:
            npis.append(""); specialties.append(""); validated.append(False)

    sources = sources.copy()
    sources["npi"] = npis
    sources["specialty"] = specialties
    sources["nppes_validated"] = validated
    return sources


def merge_group(group):
    """Merge all source rows for one resolved NPI into a single lead record."""
    rec = {
        "npi": group.name,
        "specialty": group["specialty"].iloc[0],
        "first_name": group["first_name"].iloc[0],
        "last_name": group["last_name"].iloc[0],
        "state": group["state"].iloc[0],
        "sources_seen": ",".join(sorted(group["source"].unique())),
    }
    for field, priority in FIELD_PRIORITY.items():
        value = ""
        for src in priority:
            candidates = group.loc[group["source"] == src, field]
            candidates = candidates[candidates != ""]
            if not candidates.empty:
                value = candidates.iloc[0]
                break
        rec[field] = value
    return rec


def run():
    registry = load_registry()
    sources = load_sources()
    print(f"Loaded {len(sources)} raw scraped rows across {sources['source'].nunique()} sources")

    resolved = attach_npi(sources, registry)
    validated = resolved[resolved["nppes_validated"]]
    unvalidated = resolved[~resolved["nppes_validated"]]
    print(f"NPPES-validated rows: {len(validated)}  |  unvalidated/off-registry rows: {len(unvalidated)}")

    merged = validated.groupby("npi").apply(merge_group, include_groups=False).tolist()
    leads = pd.DataFrame(merged)

    fields = ["first_name", "last_name", "practice_name", "phone", "email", "linkedin_url"]
    leads["completeness_score"] = leads[fields].apply(lambda r: sum(v != "" for v in r) / len(fields), axis=1)

    leads.sort_values("completeness_score", ascending=False).to_csv(
        OUT_DIR / "enriched_leads.csv", index=False
    )
    unvalidated.to_csv(OUT_DIR / "unvalidated_flagged.csv", index=False)

    print(f"\n=== Enrichment results ===")
    print(f"Unique NPPES-verified providers resolved from {sources['source'].nunique()} sources: {len(leads)}")
    print(f"Average completeness score (of 6 fields): {leads['completeness_score'].mean():.1%}")
    print(f"Fully complete leads (6/6 fields): {(leads['completeness_score'] == 1.0).sum()}")
    print(f"Flagged unvalidated/off-registry rows (excluded from lead list): {len(unvalidated)}")
    print(f"\nOutput: {OUT_DIR/'enriched_leads.csv'}")
    print(f"Output: {OUT_DIR/'unvalidated_flagged.csv'}")


if __name__ == "__main__":
    run()
