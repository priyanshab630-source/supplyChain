"""
P0 scaffolding: adds the two pieces of business-context metadata the
switchover/shipment-delay/allocation work depends on -
switchover_group + default_role per tank, and contract_share per
supplier per gas - as DUMMY values, so the rest of the pipeline
(BACKS_UP seeding, the ablation) is buildable and testable today.

REPLACE the dummy pairing/share logic below with real values from
Intel as soon as they're available - nothing downstream needs to
change, only this generation step, since everything else reads the
resulting tank_master/supplier_contract_shares tables, not this
file's logic directly.

Run after seed_from_csv.py:

    python -m PROJECT.data_loader.add_switchover_and_contract_data
"""

import pandas as pd

from PROJECT.database.postgres import data_engine

# Business rule:
# - Gas A: always-on pair, no standby
# - Gas C: all tanks always online simultaneously
# - Gas B/D/E/F/G: one online, one standby per pair
ALWAYS_ONLINE_GASES = {"Gas A", "Gas C"}


def _assign_switchover_groups(tank_df: pd.DataFrame) -> pd.DataFrame:

    tank_df = tank_df.copy()
    tank_df["switchover_group"] = None
    tank_df["default_role"] = None

    for gas, group_df in tank_df.groupby("gas"):
        tank_ids = group_df["tank_id"].tolist()
        always_online = gas in ALWAYS_ONLINE_GASES
        for i in range(0, len(tank_ids), 2):
            pair = tank_ids[i:i + 2]
            group_name = f"{gas.replace(' ', '')}-Group-{i // 2 + 1}"
            for j, tank_id in enumerate(pair):
                role = (
                    "ALWAYS_ONLINE" if always_online
                    else ("ONLINE" if j == 0 else "STANDBY")
                )
                tank_df.loc[tank_df["tank_id"] == tank_id, "switchover_group"] = group_name
                tank_df.loc[tank_df["tank_id"] == tank_id, "default_role"] = role

    return tank_df


def _assign_contract_shares(info_df: pd.DataFrame, tank_df: pd.DataFrame) -> pd.DataFrame:
    merged = info_df.merge(tank_df[["tank_id", "gas"]], on="tank_id", how="left")
    rows = []
    for gas, group_df in merged.groupby("gas"):
        suppliers = group_df["Suppplier_name"].dropna().unique().tolist()
        if not suppliers:
            continue

        share = round(1.0 / len(suppliers), 4)
        for supplier in suppliers:
            rows.append({"gas": gas, "supplier_name": supplier, "contract_share": share})

    return pd.DataFrame(rows)


def run():

    tank_df = pd.read_sql_table("tank_master", data_engine)
    info_df = pd.read_sql_table("supplier_info", data_engine)

    updated_tank_df = _assign_switchover_groups(tank_df)
    contract_share_df = _assign_contract_shares(info_df, updated_tank_df)

    updated_tank_df.to_sql("tank_master", data_engine, if_exists="replace", index=False)
    contract_share_df.to_sql("supplier_contract_shares", data_engine, if_exists="replace", index=False)

    print(f"Updated tank_master with switchover_group/default_role ({len(updated_tank_df)} rows).")
    print(f"Created supplier_contract_shares ({len(contract_share_df)} rows).")


if __name__ == "__main__":
    run()
