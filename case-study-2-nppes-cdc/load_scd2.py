"""
SCD2 (Slowly Changing Dimension, Type 2) loader for monthly NPPES snapshots.

This is the core of the "we manage your warehouse continuously" retainer
pitch: instead of overwriting last month's table with this month's file
(losing history), every change is captured as a new row with effective/end
dates, and the current record is flagged — so a client can always ask
"what did this provider's specialty look like on July 1st" or "when did
this NPI get deactivated" and get a real answer.

Table: hcp_master
  npi, first_name, last_name, specialty, practice_name, state, zip, phone,
  npi_deactivation_date,
  effective_date, end_date, is_current, change_reason

Usage:
    python load_scd2.py            # builds warehouse.db from scratch,
                                    # loads Aug then Sep snapshot
"""
import sqlite3
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = Path(__file__).parent / "warehouse.db"

TRACKED_FIELDS = ["specialty", "practice_name", "state", "zip", "phone"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS hcp_master (
    surrogate_key      INTEGER PRIMARY KEY AUTOINCREMENT,
    npi                TEXT NOT NULL,
    first_name         TEXT,
    last_name          TEXT,
    specialty          TEXT,
    practice_name      TEXT,
    state              TEXT,
    zip                TEXT,
    phone              TEXT,
    npi_deactivation_date TEXT,
    effective_date     TEXT NOT NULL,
    end_date           TEXT,
    is_current         INTEGER NOT NULL,
    change_reason      TEXT
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def load_snapshot(conn, csv_path, snapshot_date):
    snapshot = pd.read_csv(csv_path, dtype=str).fillna("")
    current = pd.read_sql(
        "SELECT * FROM hcp_master WHERE is_current = 1", conn
    ).set_index("npi") if _table_has_rows(conn) else pd.DataFrame().set_index(pd.Index([], name="npi"))

    inserted = updated = deactivated = unchanged = 0
    cur = conn.cursor()

    for _, row in snapshot.iterrows():
        npi = row["npi"]
        if npi not in current.index:
            # brand new provider
            _insert_new(cur, row, snapshot_date, "NEW_PROVIDER")
            inserted += 1
            continue

        existing = current.loc[npi]
        changed_fields = [f for f in TRACKED_FIELDS if existing[f] != row[f]]
        newly_deactivated = (not existing["npi_deactivation_date"]) and bool(row["npi_deactivation_date"])

        if newly_deactivated:
            _expire(cur, existing["surrogate_key"], snapshot_date)
            _insert_new(cur, row, snapshot_date, "DEACTIVATED")
            deactivated += 1
        elif changed_fields:
            _expire(cur, existing["surrogate_key"], snapshot_date)
            reason = "CHANGED:" + ",".join(changed_fields)
            _insert_new(cur, row, snapshot_date, reason)
            updated += 1
        else:
            unchanged += 1

    conn.commit()
    print(f"\n[{snapshot_date}] loaded {len(snapshot)} rows from {csv_path.name}")
    print(f"  new providers : {inserted}")
    print(f"  updated       : {updated}")
    print(f"  deactivated   : {deactivated}")
    print(f"  unchanged     : {unchanged}")


def _table_has_rows(conn):
    return conn.execute("SELECT COUNT(*) FROM hcp_master").fetchone()[0] > 0


def _insert_new(cur, row, effective_date, reason):
    cur.execute(
        """INSERT INTO hcp_master
           (npi, first_name, last_name, specialty, practice_name, state, zip,
            phone, npi_deactivation_date, effective_date, end_date, is_current, change_reason)
           VALUES (?,?,?,?,?,?,?,?,?,?,NULL,1,?)""",
        (
            row["npi"], row["first_name"], row["last_name"], row["specialty"],
            row["practice_name"], row["state"], row["zip"], row["phone"],
            row["npi_deactivation_date"], effective_date, reason,
        ),
    )


def _expire(cur, surrogate_key, end_date):
    cur.execute(
        "UPDATE hcp_master SET is_current = 0, end_date = ? WHERE surrogate_key = ?",
        (end_date, int(surrogate_key)),
    )


if __name__ == "__main__":
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = get_conn()
    load_snapshot(conn, DATA_DIR / "nppes_2026_08.csv", "2026-08-01")
    load_snapshot(conn, DATA_DIR / "nppes_2026_09.csv", "2026-09-01")

    print("\n=== Example: point-in-time query ===")
    print("Provider history for a changed NPI (first one found):")
    example_npi = conn.execute(
        "SELECT npi FROM hcp_master GROUP BY npi HAVING COUNT(*) > 1 LIMIT 1"
    ).fetchone()
    if example_npi:
        history = pd.read_sql(
            "SELECT npi, specialty, practice_name, phone, effective_date, end_date, is_current, change_reason "
            "FROM hcp_master WHERE npi = ? ORDER BY effective_date",
            conn, params=(example_npi[0],),
        )
        print(history.to_string(index=False))

    conn.close()
    print(f"\nWarehouse written to {DB_PATH}")
