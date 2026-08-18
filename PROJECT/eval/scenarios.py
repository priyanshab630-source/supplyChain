"""
P8: scenario generation.

The key design choice versus the original kg_ablation.py's
hand-written 2-scenario list: every generator below derives its
scenarios FROM THE LIVE DATA ITSELF (tank_master's switchover_group,
Neo4j's actual BACKS_UP edges, supplier_contract_shares, each tank's
real current days_of_cover) rather than hardcoding tank/supplier
names. Two consequences:

1. Coverage scales automatically - seed more switchover groups or
   BACKS_UP relationships and the eval suite exercises more of them
   with zero new scenario-writing.
2. It's a genuine regression/consistency check even while P7 is
   blocked: "given the data that's actually loaded (dummy or real),
   does the system behave correctly relative to it" is answerable
   today; "does it match my hand-guessed expected tank id" was never
   really testing the system, it was testing whether the guess was
   right.

Trade-off worth naming honestly: if the LOGIC that generates
BACKS_UP edges or switchover_group assignments is itself wrong, these
scenarios will happily validate the wrong behavior, since expected
answers are derived from the same source the system reads. That's a
real limit of this approach, not a bug in it - once P7 lands, spot-
check a handful of these generated scenarios against Intel's real
pairing by hand before trusting the eval suite's numbers blindly.
"""

import pandas as pd

from PROJECT.data_loader.loader import load_tank_master_data
from PROJECT.database.postgres import data_engine
from PROJECT.database.neo4j import get_graph
from PROJECT.tools.supplier_tools import supplier_agent as supplier_engine
from PROJECT.tools.inventory_tools import inventory_agent as inventory_engine
from PROJECT.tools.tank_status_tools import apply_surge_adjustment


def generate_malfunction_scenarios(max_scenarios: int = 20) -> list:
    """
    One scenario per switchover_group with 2+ tanks: fail the first
    tank in the group, expect the backup to be ANY other healthy tank
    in that group - a SET of acceptable answers, not one exact id, so
    this is correct for pooled Gas-C groups with 3+ tanks and not
    just simple pairs.
    """

    tank_df = load_tank_master_data(force_refresh=True)
    scenarios = []

    groups = tank_df.dropna(subset=["switchover_group"]).groupby("switchover_group")

    for group_name, group_df in groups:
        tank_ids = group_df["tank_id"].tolist()

        if len(tank_ids) < 2:
            continue

        failed = tank_ids[0]
        acceptable_backups = set(tank_ids[1:])

        scenarios.append({
            "tank_id": failed,
            "acceptable_backup_tank_ids": acceptable_backups,
            "group": group_name,
        })

        if len(scenarios) >= max_scenarios:
            break

    return scenarios


def generate_allocation_scenarios(max_scenarios: int = 20) -> list:
    """
    Two scenarios per gas with contracted suppliers: a plain split
    across everyone, and - if there's more than one supplier - the
    same split with the first supplier marked unavailable. That
    second case is the redistribution path P3 specifically exists
    for; it needs its own scenario, not just the happy path.
    """

    shares_df = pd.read_sql_table("supplier_contract_shares", data_engine)
    scenarios = []

    for gas, group_df in shares_df.groupby("gas"):

        suppliers = group_df["supplier_name"].dropna().unique().tolist()

        if not suppliers:
            continue

        scenarios.append({
            "gas": gas,
            "total_qty_needed": 1000.0,
            "unavailable_suppliers": [],
            "expected_supplier_count": len(suppliers),
        })

        if len(suppliers) > 1:
            scenarios.append({
                "gas": gas,
                "total_qty_needed": 1000.0,
                "unavailable_suppliers": [suppliers[0]],
                "expected_supplier_count": len(suppliers) - 1,
            })

        if len(scenarios) >= max_scenarios:
            break

    return scenarios[:max_scenarios]


def generate_shipment_delay_scenarios(max_pairs: int = 10) -> list:
    """
    For tanks with both a resolvable supplier and a real
    days_of_cover figure, generates ONE scenario where the delay is
    shorter than the tank's cover (should NOT flag at-risk) and ONE
    where it's longer (SHOULD flag at-risk) - directly testing the
    boundary condition report_delay is built around, instead of only
    ever exercising the "yes it's at risk" side.
    """

    tank_df = load_tank_master_data(force_refresh=True)
    scenarios = []

    for tank_id in tank_df["tank_id"].dropna().unique().tolist():

        if len(scenarios) >= max_pairs * 2:
            break

        supplier_name = supplier_engine.get_supplier_for_tank(tank_id)
        if not supplier_name:
            continue

        try:
            inventory = inventory_engine.run(f"show inventory of {tank_id}")
            inventory = apply_surge_adjustment(inventory)
        except Exception:
            continue

        cover = inventory.days_of_cover
        if not inventory.has_consumption_history or cover is None or cover == float("inf"):
            continue

        safe_delay = max(1, int(cover) - 1)
        risky_delay = int(cover) + 5

        scenarios.append({
            "supplier_name": supplier_name,
            "tank_id": tank_id,
            "delay_days": safe_delay,
            "expect_at_risk": False,
        })
        scenarios.append({
            "supplier_name": supplier_name,
            "tank_id": tank_id,
            "delay_days": risky_delay,
            "expect_at_risk": True,
        })

    return scenarios


def generate_kg_backup_scenarios(max_scenarios: int = 15) -> list:
    """
    Pulls every BACKS_UP edge currently in Neo4j and turns each
    source tank into a "who backs this up" question, with the
    acceptable-answer set read directly from the graph. This is what
    takes kg_ablation.py from 2 hardcoded scenarios to however many
    BACKS_UP edges actually exist - seed more via
    scripts/seed_backs_up_relationships.py and this scales with no
    code changes. Key name (`expected_tank_ids`) matches
    kg_ablation.py's existing SCENARIOS format on purpose, so it's a
    drop-in replacement there - see EVAL_README.md.
    """

    graph = get_graph()

    records = graph.query(
        """
        MATCH (a:Tank)-[:BACKS_UP]->(b:Tank)
        RETURN a.tank_id AS tank_id, collect(b.tank_id) AS backups
        """
    )

    scenarios = []

    for record in records[:max_scenarios]:
        tank_id = record.get("tank_id")
        backups = record.get("backups") or []

        if not tank_id or not backups:
            continue

        scenarios.append({
            "question": f"If {tank_id} malfunctions, which tank backs it up?",
            "expected_tank_ids": list(backups),
        })

    return scenarios