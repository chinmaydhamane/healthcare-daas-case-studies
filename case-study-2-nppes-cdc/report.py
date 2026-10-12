"""
Monthly change report — the actual client deliverable for the retainer tier:
"here's what changed in your HCP universe this month."
"""
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "warehouse.db"
OUT_DIR = Path(__file__).parent / "output"
OUT_DIR.mkdir(exist_ok=True)


def run():
    conn = sqlite3.connect(DB_PATH)

    changes = pd.read_sql(
        """SELECT npi, first_name, last_name, specialty, practice_name,
                  effective_date, change_reason
           FROM hcp_master
           WHERE effective_date = '2026-09-01'
           ORDER BY change_reason, npi""",
        conn,
    )
    changes.to_csv(OUT_DIR / "september_change_report.csv", index=False)

    summary = changes["change_reason"].apply(lambda r: r.split(":")[0]).value_counts()
    print("=== September 2026 change summary ===")
    print(summary.to_string())
    print(f"\nTotal current providers: {conn.execute('SELECT COUNT(*) FROM hcp_master WHERE is_current=1').fetchone()[0]}")
    print(f"\nFull change log written to {OUT_DIR/'september_change_report.csv'}")
    conn.close()


if __name__ == "__main__":
    run()
