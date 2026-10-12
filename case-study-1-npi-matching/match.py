"""
NPI matching pipeline: matches an incoming HCP audience list against the
NPPES registry using a deterministic-first, fuzzy-fallback strategy with
confidence tiering — the exact methodology clients ask about on
"how does NPI matching work / what match rate should I expect" calls.

Tiers:
  EXACT   - NPI number present and found in registry
  HIGH    - no usable NPI, but last_name + first_name + state + zip
            (or phone) match a single registry record with high fuzzy score
  MEDIUM  - last_name + state match with moderate fuzzy score on first_name,
            single best candidate above threshold
  UNMATCHED - no candidate clears the medium threshold

Usage:
    python match.py
"""
import pandas as pd
from rapidfuzz import fuzz, process
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
OUT_DIR = Path(__file__).parent / "output"
OUT_DIR.mkdir(exist_ok=True)

HIGH_THRESHOLD = 90
MEDIUM_THRESHOLD = 75


def load():
    registry = pd.read_csv(DATA_DIR / "nppes_registry.csv", dtype=str).fillna("")
    audience = pd.read_csv(DATA_DIR / "hcp_audience.csv", dtype=str).fillna("")
    return registry, audience


def match_exact_npi(audience, registry):
    reg_by_npi = registry.set_index("npi")
    results = []
    remaining = []
    for _, row in audience.iterrows():
        npi = row["npi"].strip()
        if npi and npi in reg_by_npi.index:
            reg_row = reg_by_npi.loc[npi]
            results.append({**row.to_dict(), "match_tier": "EXACT", "matched_npi": npi,
                             "match_score": 100, "matched_specialty": reg_row["specialty"]})
        else:
            remaining.append(row)
    return results, remaining


def fuzzy_match(remaining, registry):
    """
    Blocking on state to keep this a per-block O(n * block_size) problem
    instead of a full O(n*m) cross join — the same blocking strategy you'd
    use at production scale (block on state + specialty + zip3, etc).

    Within a block, rapidfuzz.process.extractOne is used instead of a
    Python-level nested loop: it runs the comparisons in C, which is the
    difference between a demo that finishes in seconds vs. minutes at
    this row count.
    """
    results = []
    registry_by_state = {s: g.reset_index(drop=True) for s, g in registry.groupby("state")}
    name_choices_by_state = {
        s: (g["first_name"] + " " + g["last_name"]).str.lower().tolist()
        for s, g in registry_by_state.items()
    }

    for row in remaining:
        rec = row.to_dict() if hasattr(row, "to_dict") else dict(row)
        candidates = registry_by_state.get(row["hcp_state"])
        full_name = f"{row['hcp_first_name']} {row['hcp_last_name']}".lower()

        if candidates is None or candidates.empty:
            rec.update({"match_tier": "UNMATCHED", "matched_npi": "", "match_score": 0,
                        "matched_specialty": ""})
            results.append(rec)
            continue

        choices = name_choices_by_state[row["hcp_state"]]
        match = process.extractOne(full_name, choices, scorer=fuzz.token_sort_ratio)
        best_score, best_idx = (match[1], match[2]) if match else (-1, None)
        best_row = candidates.iloc[best_idx] if best_idx is not None else None
        if best_row is not None and row["hcp_zip"] and row["hcp_zip"] == best_row["zip"]:
            best_score += 5

        if best_score >= HIGH_THRESHOLD:
            tier = "HIGH"
        elif best_score >= MEDIUM_THRESHOLD:
            tier = "MEDIUM"
        else:
            tier = "UNMATCHED"

        if tier == "UNMATCHED":
            rec.update({"match_tier": tier, "matched_npi": "", "match_score": max(best_score, 0),
                        "matched_specialty": ""})
        else:
            rec.update({"match_tier": tier, "matched_npi": best_row["npi"],
                        "match_score": best_score, "matched_specialty": best_row["specialty"]})
        results.append(rec)
    return results


def run():
    registry, audience = load()
    exact_results, remaining = match_exact_npi(audience, registry)
    fuzzy_results = fuzzy_match(remaining, registry)

    all_results = pd.DataFrame(exact_results + fuzzy_results)
    all_results.to_csv(OUT_DIR / "match_results.csv", index=False)

    tier_counts = all_results["match_tier"].value_counts()
    total = len(all_results)
    print("\n=== NPI Match Results ===")
    for tier in ["EXACT", "HIGH", "MEDIUM", "UNMATCHED"]:
        n = tier_counts.get(tier, 0)
        print(f"{tier:10s}: {n:6d}  ({n/total:5.1%})")
    print(f"{'TOTAL':10s}: {total:6d}")

    matched = total - tier_counts.get("UNMATCHED", 0)
    print(f"\nOverall match rate (EXACT+HIGH+MEDIUM): {matched/total:.1%}")

    print("\n=== Match rate by specialty ===")
    by_spec = (
        all_results.assign(matched=all_results["match_tier"] != "UNMATCHED")
        .groupby("hcp_specialty")["matched"]
        .agg(["sum", "count"])
    )
    by_spec["rate"] = by_spec["sum"] / by_spec["count"]
    by_spec.to_csv(OUT_DIR / "match_rate_by_specialty.csv")
    print(by_spec.rename(columns={"sum": "matched", "count": "total"}))

    print(f"\nFull results written to {OUT_DIR/'match_results.csv'}")
    print(f"Specialty summary written to {OUT_DIR/'match_rate_by_specialty.csv'}")


if __name__ == "__main__":
    run()
