"""
Synthetic data generator for the Lead-List Scraping & Enrichment case study.

Mirrors the "healthcare data mining specialist" brief: provider name, email,
phone, practice name, and LinkedIn URL, sourced from multiple places and
cross-validated against CMS/NPPES data — not a single clean file.

Produces:
  data/nppes_registry.csv     - source of truth (name, specialty, NPI, state)
  data/source_directory_site.csv  - a public provider-directory scrape:
                                     decent coverage of practice name/phone,
                                     rarely has email or LinkedIn
  data/source_practice_sites.csv  - scraped from individual practice
                                     websites: good email coverage, spotty
                                     phone, no LinkedIn, some records are for
                                     providers not in the registry at all
                                     (locums, retired, name variants)
  data/source_linkedin_style.csv  - professional-profile-style source:
                                     strong LinkedIn + practice name, weak
                                     contact info, some duplicate people
                                     appearing under slightly different name
                                     spellings

No real scraping is performed — this generates representative *shapes* of
data (coverage gaps, duplication, conflicting values across sources) so the
enrichment/merge logic can be demonstrated and benchmarked without touching
any real website or ToS question. In a real engagement, source selection
would be scoped explicitly against each site's terms of service and
robots.txt before any collection begins.
"""
import csv
import random
from pathlib import Path

from faker import Faker

fake = Faker()
Faker.seed(11)
random.seed(11)

OUT_DIR = Path(__file__).parent / "data"
OUT_DIR.mkdir(exist_ok=True)

SPECIALTIES = ["Cardiology", "Gastroenterology", "Primary Care", "Oncology", "Dermatology"]
STATES = ["NY", "CA", "TX", "FL", "IL"]
N_PROVIDERS = 3_000


def make_npi():
    return "1" + "".join(str(random.randint(0, 9)) for _ in range(9))


def build_registry():
    rows = []
    for _ in range(N_PROVIDERS):
        first, last = fake.first_name(), fake.last_name()
        rows.append({
            "npi": make_npi(),
            "first_name": first,
            "last_name": last,
            "specialty": random.choice(SPECIALTIES),
            "practice_name": f"{last} {random.choice(['Medical Group', 'Clinic', 'Associates'])}",
            "state": random.choice(STATES),
        })
    with open(OUT_DIR / "nppes_registry.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    return rows


def slight_name_variant(name):
    return name.upper() if random.random() < 0.2 else name


def build_directory_site(registry):
    """Good phone/practice coverage, almost never email or LinkedIn."""
    sample = random.sample(registry, int(N_PROVIDERS * 0.7))
    rows = []
    for r in sample:
        rows.append({
            "source": "directory_site",
            "first_name": slight_name_variant(r["first_name"]),
            "last_name": slight_name_variant(r["last_name"]),
            "practice_name": r["practice_name"],
            "state": r["state"],
            "phone": fake.numerify("(###) ###-####") if random.random() > 0.1 else "",
            "email": "",
            "linkedin_url": "",
        })
    with open(OUT_DIR / "source_directory_site.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    return rows


def build_practice_sites(registry):
    """Good email coverage, spotty phone, includes some off-registry noise."""
    sample = random.sample(registry, int(N_PROVIDERS * 0.5))
    rows = []
    for r in sample:
        domain = r["practice_name"].lower().replace(" ", "").replace(",", "") + ".com"
        rows.append({
            "source": "practice_site",
            "first_name": r["first_name"],
            "last_name": r["last_name"],
            "practice_name": r["practice_name"],
            "state": r["state"],
            "phone": fake.numerify("(###) ###-####") if random.random() > 0.5 else "",
            "email": f"{r['first_name'].lower()}.{r['last_name'].lower()}@{domain}",
            "linkedin_url": "",
        })
    # noise: providers not actually in the registry (retired, locum, closed practice)
    for _ in range(int(len(rows) * 0.08)):
        rows.append({
            "source": "practice_site",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "practice_name": fake.company(),
            "state": random.choice(STATES),
            "phone": fake.numerify("(###) ###-####"),
            "email": fake.email(),
            "linkedin_url": "",
        })
    with open(OUT_DIR / "source_practice_sites.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    return rows


def build_linkedin_style(registry):
    """Strong LinkedIn + practice name, weak contact info, name-spelling drift."""
    sample = random.sample(registry, int(N_PROVIDERS * 0.4))
    rows = []
    for r in sample:
        fn, ln = r["first_name"], r["last_name"]
        if random.random() < 0.1:
            ln = ln + random.choice(["", "-Smith", " Jr"])
        rows.append({
            "source": "linkedin_style",
            "first_name": fn,
            "last_name": ln,
            "practice_name": r["practice_name"],
            "state": r["state"],
            "phone": "",
            "email": "",
            "linkedin_url": f"linkedin.com/in/{fn.lower()}-{ln.lower().replace(' ', '')}",
        })
    with open(OUT_DIR / "source_linkedin_style.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    registry = build_registry()
    d = build_directory_site(registry)
    p = build_practice_sites(registry)
    l = build_linkedin_style(registry)
    print(f"Registry: {len(registry)} providers")
    print(f"Directory site source: {len(d)} rows")
    print(f"Practice site source: {len(p)} rows")
    print(f"LinkedIn-style source: {len(l)} rows")
