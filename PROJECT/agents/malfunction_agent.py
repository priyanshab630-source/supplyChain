"""
P2: Tank malfunction handling.

Given a tank reported as malfunctioning:
1. Mark it MALFUNCTION in tank_status.
2. Find its backup tank via the BACKS_UP relationship in Neo4j
   (seeded by scripts/seed_backs_up_relationships.py).
3. Activate the backup (STANDBY -> ONLINE; for an ALWAYS_ONLINE
   tank, no status change is needed - it's already online, only the
   surge applies).
4. Apply a surge multiplier to the backup tank's status row, so
   every future inventory/forecast/risk call on that tank
   automatically reflects it absorbing the failed tank's load (see
   tools/tank_status_tools.py - this is the P6 hook).
5. Recompute the backup tank's days of cover under the surged rate
   right now, via apply_surge_adjustment() - the SAME function
   inventory_node/forecast_node/shipment_delay_agent all call, so
   there is exactly one place in the codebase that knows what
   "surged" means. (Previously this step reimplemented the
   multiplier math inline, which happened to agree with
   apply_surge_adjustment only because both were kept in sync by
   hand - a real drift risk if the surge formula ever changes.)
"""
from langsmith import traceable
from PROJECT.database.neo4j import get_graph
from PROJECT.data_loader.loader import load_tank_status, write_tank_status
from PROJECT.tools.inventory_tools import inventory_agent as inventory_engine
from PROJECT.tools.tank_status_tools import apply_surge_adjustment
from PROJECT.models.malfunction_models import MalfunctionResult


DEFAULT_SURGE_MULTIPLIER = 1.5


EMERGENCY_DAYS_OF_COVER_THRESHOLD = 2.0

class MalfunctionAgent:

    def _find_backup_tank(self, tank_id: str):
        """
        Returns the first tank connected to tank_id via BACKS_UP that
        isn't itself already in MALFUNCTION status, or None if no
        usable backup exists.
        """

        graph = get_graph()

        records = graph.query(
            """
            MATCH (failed:Tank {tank_id: $tank_id})-[:BACKS_UP]->(backup:Tank)
            RETURN backup.tank_id AS backup_tank_id
            """,
            {"tank_id": tank_id},
        )

        status_df = load_tank_status()

        for record in records:
            candidate = record.get("backup_tank_id")
            if candidate is None:
                continue

            candidate_status_rows = status_df.loc[status_df["tank_id"] == candidate, "status"]
            current_status = candidate_status_rows.iloc[0] if not candidate_status_rows.empty else None

            if current_status != "MALFUNCTION":
                return candidate

        return None

    @traceable(name="MalfunctionAgent.report_malfunction", run_type="chain")
    def report_malfunction(self, tank_id: str) -> MalfunctionResult:
        write_tank_status(tank_id, status="MALFUNCTION", surge_multiplier=1.0)

        backup_tank_id = self._find_backup_tank(tank_id)

        if backup_tank_id is None:
            return MalfunctionResult(
                failed_tank_id=tank_id,
                backup_tank_id=None,
                backup_activated=False,
                surge_multiplier_applied=None,
                adjusted_days_of_cover=None,
                emergency_delivery_needed=True,
                reasoning=(
                    f"{tank_id} has no available backup tank (either none is "
                    "defined in the graph, or its only backup is also in "
                    "MALFUNCTION status). Treat this as an emergency - there "
                    "is no automatic failover available for this tank."
                ),
            )

        status_df = load_tank_status()
        backup_row = status_df.loc[status_df["tank_id"] == backup_tank_id]
        current_backup_status = backup_row.iloc[0]["status"] if not backup_row.empty else "STANDBY"

        new_status = "ONLINE" if current_backup_status != "ALWAYS_ONLINE" else "ALWAYS_ONLINE"

        write_tank_status(
            backup_tank_id,
            status=new_status,
            surge_multiplier=DEFAULT_SURGE_MULTIPLIER,
            compensating_for=tank_id,  
        )
        try:
            inventory = inventory_engine.run(f"show inventory of {backup_tank_id}")
            inventory = apply_surge_adjustment(inventory)
            adjusted_days_of_cover = inventory.days_of_cover

        except Exception:
            adjusted_days_of_cover = None

        emergency_needed = (
            adjusted_days_of_cover is not None
            and adjusted_days_of_cover < EMERGENCY_DAYS_OF_COVER_THRESHOLD
        )

        if adjusted_days_of_cover is not None:
            reasoning = (
                f"{tank_id} marked MALFUNCTION. {backup_tank_id} activated as "
                f"backup with a {DEFAULT_SURGE_MULTIPLIER}x consumption surge "
                f"applied. Adjusted days of cover under the surged rate: "
                f"{adjusted_days_of_cover:.2f}."
            )
        else:
            reasoning = (
                f"{tank_id} marked MALFUNCTION. {backup_tank_id} activated as "
                f"backup with a {DEFAULT_SURGE_MULTIPLIER}x consumption surge "
                f"applied. Could not recompute its days of cover right now."
            )

        return MalfunctionResult(
            failed_tank_id=tank_id,
            backup_tank_id=backup_tank_id,
            backup_activated=True,
            surge_multiplier_applied=DEFAULT_SURGE_MULTIPLIER,
            adjusted_days_of_cover=adjusted_days_of_cover,
            emergency_delivery_needed=emergency_needed,
            reasoning=reasoning,
        )


malfunction_agent = MalfunctionAgent()