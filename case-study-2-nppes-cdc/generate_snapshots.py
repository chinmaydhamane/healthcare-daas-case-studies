"""
Synthetic month-over-month NPPES snapshot generator for the
Change-Data-Capture / SCD2 retainer case study.

Produces:
  data/nppes_2026_08.csv  - "last month" snapshot
  data/nppes_2026_09.csv  - "this month" snapshot, derived from the first
                            with realistic month-over-month churn:
                              - ~2% brand new NPIs (new providers)
                              - ~1% deactivated (present last month, gone now)
                              - ~4% changed practice/address/phone
                              - ~1.5% changed specialty/taxonomy
                              - everything else unchanged

This mirrors what actually happens between two monthly NPPES bulk files —
the retainer-tier pitch ("we keep your warehouse current every month") only
means something if you can show the diff logic working.
"""
import csv
import random
from pathlib import Path

from faker import Faker

fake = Faker()
Faker.seed(7)
random.seed(7)

OUT_DIR = Path(__file__).parent / "data"
OUT_DIR.mkdir(exist_ok=True)

SPECIALTIES = [
    "Cardiology", "Gastroenterology", "Primary Care",
    "Oncology", "Dermatology", "Orthopedics",
]
STATES = ["NY", "CA", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]

N_PROVIDERS = 5_000


def make_npi(existing):
    while True:
        npi = "1" + "".join(str(random.randint(0, 9)) for _ in range(9))
        if npi not in existing:
            return npi


def build_base_snapshot():
    rows = []
    seen_npi = set()
    for _ in range(N_PROVIDERS):
        npi = make_npi(seen_npi)
        seen_npi.add(npi)
        last = fake.last_name()
        rows.append(
            {
                "npi": npi,
                "first_name": fake.first_name(),
                "last_name": last,
                "specialty": random.choice(SPECIALTIES),
                "practice_name": f"{last} {random.choice(['Medical Group', 'Clinic', 'Associates', 'Health Partners'])}",
                "state": random.choice(STATES),
                "zip": fake.zipcode(),
                "phone": fake.numerify("(###) ###-####"),
                "npi_deactivation_date": "",
            }
        )
    return rows


def derive_next_snapshot(base_rows):
    rows = [dict(r) for r in base_rows]
    existing_npis = {r["npi"] for r in rows}

    n = len(rows)
    n_new = int(n * 0.02)
    n_deactivated = int(n * 0.01)
    n_address_change = int(n * 0.04)
    n_specialty_change = int(n * 0.015)

    # deactivations
    for r in random.sample(rows, n_deactivated):
        r["npi_deactivation_date"] = "2026-09-15"

    # address/practice/phone changes
    active = [r for r in rows if not r["npi_deactivation_date"]]
    for r in random.sample(active, min(n_address_change, len(active))):
        r["practice_name"] = f"{r['last_name']} {random.choice(['Medical Group', 'Health Network', 'Physicians LLC'])}"
        r["phone"] = fake.numerify("(###) ###-####")
        r["zip"] = fake.zipcode()

    # specialty/taxonomy changes (e.g. re-credentialed, sub-specialization)
    for r in random.sample(active, min(n_specialty_change, len(active))):
        r["specialty"] = random.choice([s for s in SPECIALTIES if s != r["specialty"]])

    # new providers
    for _ in range(n_new):
        npi = make_npi(existing_npis)
        existing_npis.add(npi)
        last = fake.last_name()
        rows.append(
            {
                "npi": npi,
                "first_name": fake.first_name(),
                "last_name": last,
                "specialty": random.choice(SPECIALTIES),
                "practice_name": f"{last} {random.choice(['Medical Group', 'Clinic', 'Associates'])}",
                "state": random.choice(STATES),
                "zip": fake.zipcode(),
                "phone": fake.numerify("(###) ###-####"),
                "npi_deactivation_date": "",
            }
        )
    return rows


def write(rows, filename):
    fieldnames = [
        "npi", "first_name", "last_name", "specialty", "practice_name",
        "state", "zip", "phone", "npi_deactivation_date",
    ]
    with open(OUT_DIR / filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows -> {OUT_DIR/filename}")


if __name__ == "__main__":
    august = build_base_snapshot()
    september = derive_next_snapshot(august)
    write(august, "nppes_2026_08.csv")
    write(september, "nppes_2026_09.csv")
