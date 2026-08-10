"""
One-time (or re-run-when-needed) migration: loads your existing
static CSVs into the database tables the dynamic loader reads from.
Run this once before starting the app, and again any time you
replace a CSV with a new export.

    python -m PROJECT.data_loader.seed_from_csv
"""

import pandas as pd

from PROJECT.database.postgres import data_engine

# Adjust these paths to wherever your CSVs actually live (your repo
# has a data/ folder at the root per the earlier screenshot).
CSV_PATHS = {
    "tank_master": "data/Tanks-Master-Data.csv",
    "supplier_info": "data/Supplier-Info.csv",
    "consumption_readings": "data/Consumption-Data.csv",
    "supplier_schedule": "data/Supplier-Schedule.csv",
}


def seed():

    for table_name, path in CSV_PATHS.items():
        df = pd.read_csv(path)
        df.to_sql(table_name, data_engine, if_exists="replace", index=False)
        print(f"Seeded '{table_name}' ({len(df)} rows) from {path}")


if __name__ == "__main__":
    seed()
