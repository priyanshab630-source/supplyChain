"""
Optional one-time seed: populates tank_status for every tank from
tank_master's default_role column (ONLINE/STANDBY/ALWAYS_ONLINE), so
the operational-status table reflects each tank's normal role from
the start, rather than only gaining rows as malfunctions get
reported. Not required for correctness (see loader.py's
write_tank_status docstring), but makes STANDBY vs ONLINE vs
ALWAYS_ONLINE visible from day one instead of only after the first
malfunction touches a given tank.

Run after add_switchover_and_contract_data.py (which is what adds
the default_role column):

    python -m PROJECT.data_loader.init_tank_status
"""

import pandas as pd

from PROJECT.database.postgres import data_engine
from PROJECT.data_loader.loader import write_tank_status


def run():

    tank_df = pd.read_sql_table("tank_master", data_engine)

    if "default_role" not in tank_df.columns:
        raise RuntimeError(
            "tank_master has no default_role column yet - run "
            "add_switchover_and_contract_data.py first."
        )

    count = 0

    for _, row in tank_df.iterrows():

        status = row.get("default_role") or "ONLINE"
        write_tank_status(row["tank_id"], status=status, surge_multiplier=1.0)
        count += 1

    print(f"Initialized tank_status for {count} tanks.")


if __name__ == "__main__":
    run()
