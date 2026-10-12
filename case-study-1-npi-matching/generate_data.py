"""
Synthetic data generator for the NPI Matching Benchmark case study.

Produces two files:
  data/nppes_registry.csv  - stand-in for the public NPPES NPI Registry
                              (clean "source of truth" provider records)
  data/hcp_audience.csv    - stand-in for a purchased/scraped HCP audience
                              list, deliberately degraded (typos, missing
                              NPI, formatting drift) the way real third-party
                              lists arrive.

This lets the matching pipeline be demoed and benchmarked without needing
the multi-GB real NPPES download.
"""
import csv
import random
from pathlib import Path

from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

OUT_DIR = Path(__file__).parent / "data"
OUT_DIR.mkdir(exist_ok=True)

SPECIALTIES = [
    "Cardiology",
    "Gastroenterology",
    "Primary Care",
    "Oncology",
    "Dermatology",
    "Orthopedics",
]

STATES = ["NY", "CA", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]

N_PROVIDERS = 20_000


def make_npi():
    return "1" + "".join(str(random.randint(0, 9)) for _ in range(9))


def build_registry():
    rows = []
    for _ in range(N_PROVIDERS):
        first, last = fake.first_name(), fake.last_name()
        rows.append(
            {
                "npi": make_npi(),
                "first_name": first,
                "last_name": last,
                "specialty": random.choice(SPECIALTIES),
                "practice_name": f"{last} {random.choice(['Medical Group', 'Clinic', 'Associates', 'Health Partners'])}",
                "state": random.choice(STATES),
                "zip": fake.zipcode(),
                "phone": fake.numerify("(###) ###-####"),
                "license_number": fake.bothify("??######").upper(),
            }
        )
    with open(OUT_DIR / "nppes_registry.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return rows


def degrade_name(name):
    """Simulate common scrape/entry typos."""
    if random.random() < 0.15 and len(name) > 3:
        i = random.randint(1, len(name) - 2)
        name = name[:i] + name[i + 1] + name[i] + name[i + 2 :]  # swap two chars
    if random.random() < 0.1:
        name = name.upper()
    return name


def build_audience(registry):
    """
    Sample ~60% of the registry to be the 'audience' list, then degrade it:
      - drop NPI on 40% of rows (common: purchased lists rarely include NPI)
      - typo names on ~15%
      - drop/garble phone on 20%
      - occasionally swap specialty label wording
      - add 10% totally unmatched noise records (people not in registry)
    """
    sample = random.sample(registry, int(N_PROVIDERS * 0.6))
    audience = []
    for r in sample:
        row = dict(r)
        row["hcp_first_name"] = degrade_name(row.pop("first_name"))
        row["hcp_last_name"] = degrade_name(row.pop("last_name"))
        row["hcp_specialty"] = row.pop("specialty")
        row["hcp_practice_name"] = row.pop("practice_name")
        row["hcp_state"] = row.pop("state")
        row["hcp_zip"] = row.pop("zip")
        row["hcp_phone"] = row.pop("phone") if random.random() > 0.2 else ""
        row.pop("license_number", None)
        if random.random() < 0.4:
            row["npi"] = ""  # missing NPI — the realistic, common case
        audience.append(row)

    # noise: people not actually in the registry at all
    n_noise = int(len(audience) * 0.1)
    for _ in range(n_noise):
        audience.append(
            {
                "npi": "",
                "hcp_first_name": fake.first_name(),
                "hcp_last_name": fake.last_name(),
                "hcp_specialty": random.choice(SPECIALTIES),
                "hcp_practice_name": fake.company(),
                "hcp_state": random.choice(STATES),
                "hcp_zip": fake.zipcode(),
                "hcp_phone": fake.numerify("(###) ###-####"),
            }
        )

    random.shuffle(audience)
    fieldnames = [
        "npi",
        "hcp_first_name",
        "hcp_last_name",
        "hcp_specialty",
        "hcp_practice_name",
        "hcp_state",
        "hcp_zip",
        "hcp_phone",
    ]
    with open(OUT_DIR / "hcp_audience.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in audience:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    return audience


if __name__ == "__main__":
    registry = build_registry()
    audience = build_audience(registry)
    print(f"Wrote {len(registry)} registry rows -> {OUT_DIR/'nppes_registry.csv'}")
    print(f"Wrote {len(audience)} audience rows -> {OUT_DIR/'hcp_audience.csv'}")
