"""
P4: Shipment delay handling.

Two distinct events are handled here, deliberately NOT collapsed
into one code path with an extreme input:

- report_delay(): a shipment is late by a KNOWN number of days. Order
  sizing targets (delay_days + REORDER_BUFFER_DAYS).
- report_outage(): a supplier can't deliver at all, with NO known
  delivery date. Every tank it serves is at risk by definition -
  there's no "will it arrive in time" question when nothing is
  arriving - and order sizing targets a fixed OUTAGE_REORDER_TARGET_DAYS
  window (same 14-day precedent RecommendationAgent uses for a
  routine reorder), not a delay length that doesn't exist.

  (Earlier version modeled an outage as report_delay(..., 999) - that
  silently fed 999 into the SAME order-sizing formula used for real
  delays, producing target_inventory = avg_daily * 1001 days: a
  reallocation request for roughly three years of gas. Sharing the
  ALLOCATION-BUILDING code between the two paths is fine and intended;
  sharing the DELAY-LENGTH NUMBER was the bug.)

Both paths reuse the same _build_alternate_allocation() helper - it
takes an explicit target_days + a human-readable label, so it has no
opinion on where those came from. That's the one place order sizing
happens; report_delay/report_outage just decide what to feed it.
"""

from PROJECT.data_loader.loader import write_shipment_status
from PROJECT.tools.inventory_tools import (
    inventory_agent as inventory_engine,
    tank_df as tank_master_df,
)
from PROJECT.tools.tank_status_tools import apply_surge_adjustment
from PROJECT.tools.supplier_tools import supplier_agent as supplier_engine
from PROJECT.agents.allocation_agent import allocation_agent
from PROJECT.models.shipment_models import ShipmentDelayResult, TankDelayImpact
from langsmith import traceable



DELAY_RISK_BUFFER_DAYS = 0.0
REORDER_BUFFER_DAYS = 2
OUTAGE_REORDER_TARGET_DAYS = 14

class ShipmentDelayAgent:

    def _affected_tanks(self, supplier_name: str, tank_id: str = None) -> list:
        if tank_id:
            return [tank_id]

        tanks = supplier_engine.get_supplier_tanks(supplier_name)
        if not tanks:
            raise ValueError(
                f"No tanks found for supplier '{supplier_name}' - check the "
                "spelling, or whether this supplier exists in the supplier/"
                "tank master data."
            )

        return tanks

    def _assess_tank_for_delay(self, tank_id: str, delay_days: int) -> TankDelayImpact:
        try:
            inventory = inventory_engine.run(f"show inventory of {tank_id}")
            inventory = apply_surge_adjustment(inventory)

        except Exception as exc:
            return TankDelayImpact(
                tank_id=tank_id,
                days_of_cover=None,
                will_stockout_before_delivery=None,
                error=str(exc),
            )

        days_of_cover = inventory.days_of_cover
        will_stockout = (
            days_of_cover is not None
            and days_of_cover != float("inf")
            and days_of_cover <= (delay_days - DELAY_RISK_BUFFER_DAYS)
        )

        return TankDelayImpact(
            tank_id=tank_id,
            days_of_cover=days_of_cover,
            will_stockout_before_delivery=will_stockout,
        )

    def _assess_tank_for_outage(self, tank_id: str) -> TankDelayImpact:
        """
        No known delivery date means every tank is at risk by
        definition - days_of_cover is still reported for context/
        urgency, but doesn't gate the risk flag the way it does for a
        finite delay.
        """

        try:
            inventory = inventory_engine.run(f"show inventory of {tank_id}")
            inventory = apply_surge_adjustment(inventory)
            days_of_cover = inventory.days_of_cover

        except Exception as exc:
            return TankDelayImpact(
                tank_id=tank_id,
                days_of_cover=None,
                will_stockout_before_delivery=True,
                error=str(exc),
            )

        return TankDelayImpact(
            tank_id=tank_id,
            days_of_cover=days_of_cover,
            will_stockout_before_delivery=True,
        )

    def _resolve_gas_for_tank(self, tank_id: str):
        rows = tank_master_df.loc[tank_master_df["tank_id"] == tank_id, "gas"]
        return rows.iloc[0] if not rows.empty else None

    def _order_qty_for_tank(self, inventory, target_days: float) -> float:
        """
        How much gas THIS tank needs ordered to be covered through
        target_days - mirrors RecommendationAgent.recommend_order_qty's
        (target_inventory - current_inventory) shape. target_days is
        supplied by the caller (report_delay or report_outage) - this
        method has no opinion on whether that number came from a
        known delay or a fixed outage window.
        """

        if not inventory.has_consumption_history or not inventory.avg_daily_consumption:
            return 0.0

        target_inventory = inventory.avg_daily_consumption * target_days
        current = inventory.current_inventory or 0

        return max(target_inventory - current, 0.0)

    def _build_alternate_allocation(self, supplier_name: str, at_risk: list, target_days: float, situation_label: str,):
        """
        Tries to reallocate the at-risk tanks' gas order across the
        supplier's remaining contracted partners. Returns
        (alternate_allocation_or_None, recommended_action_text).
        Never raises - a failure here degrades to a plain-language
        recommendation instead of blocking the whole report.
        """

        gas = self._resolve_gas_for_tank(at_risk[0].tank_id)

        if not gas:
            return None, (
                f"{len(at_risk)} tank(s) are at risk due to {situation_label}, and "
                "this tank's gas type could not be resolved for reallocation - "
                "expedite an earlier delivery or arrange an emergency shipment."
            )

        try:
            total_qty_needed = sum(
                self._order_qty_for_tank(
                    apply_surge_adjustment(inventory_engine.run(f"show inventory of {i.tank_id}")),
                    target_days,
                )
                for i in at_risk
            )

            alternate_allocation = allocation_agent.allocate(
                gas=gas,
                total_qty_needed=total_qty_needed,
                unavailable_suppliers=[supplier_name],
            )

            recommended_action = (
                f"{len(at_risk)} tank(s) are at risk due to {situation_label}. "
                f"Reallocate {total_qty_needed:,.0f} units of {gas} across the "
                "remaining contracted supplier(s) below, or expedite an earlier "
                "delivery if reallocation isn't possible."
            )

            return alternate_allocation, recommended_action

        except Exception:
            return None, (
                f"{len(at_risk)} tank(s) are at risk due to {situation_label}, and "
                f"no alternate contracted supplier could be found for {gas} - "
                "expedite an earlier delivery or arrange an emergency shipment."
            )

    @traceable(name="ShipmentDelayAgent.report_delay", run_type="chain")
    def report_delay(self, supplier_name: str, delay_days: int, tank_id: str = None,) -> ShipmentDelayResult:

        affected_tanks = self._affected_tanks(supplier_name, tank_id)
        impacts = []
        for t_id in affected_tanks:
            impact = self._assess_tank_for_delay(t_id, delay_days)
            impacts.append(impact)

            write_shipment_status(
                supplier_name=supplier_name,
                tank_id=t_id,
                delay_days=delay_days,
                status="DELAYED",
            )

        at_risk = [i for i in impacts if i.will_stockout_before_delivery]

        alternate_allocation = None
        recommended_action = (
            "Monitor - no tank is expected to stock out before the "
            "delayed shipment arrives."
        )

        if at_risk:
            target_days = delay_days + REORDER_BUFFER_DAYS
            situation_label = (
                f"the {delay_days}-day delay from {supplier_name} "
                f"(order sized to cover {delay_days} days plus a "
                f"{REORDER_BUFFER_DAYS}-day buffer)"
            )
            alternate_allocation, recommended_action = self._build_alternate_allocation(
                supplier_name, at_risk, target_days, situation_label
            )

        reasoning = (
            f"{supplier_name}'s shipment delayed by {delay_days} day(s), affecting "
            f"{len(impacts)} tank(s). {len(at_risk)} tank(s) are projected to run out "
            "of inventory before the delayed shipment now arrives."
        )

        return ShipmentDelayResult(
            supplier_name=supplier_name,
            delay_days=delay_days,
            tank_impacts=impacts,
            tanks_at_risk=[i.tank_id for i in at_risk],
            recommended_action=recommended_action,
            alternate_allocation=alternate_allocation,
            reasoning=reasoning,
        )

    @traceable(name="ShipmentDelayAgent.report_outage", run_type="chain")
    def report_outage(self, supplier_name: str) -> ShipmentDelayResult:
        """
        Total outage, no known delivery date. Every tank the supplier
        serves is treated as at risk by definition - order sizing
        uses OUTAGE_REORDER_TARGET_DAYS, not a delay-length surrogate.
        """

        affected_tanks = self._affected_tanks(supplier_name, tank_id=None)
        impacts = [self._assess_tank_for_outage(t_id) for t_id in affected_tanks]

        for t_id in affected_tanks:
            write_shipment_status(
                supplier_name=supplier_name,
                tank_id=t_id,
                delay_days=0,
                status="OUTAGE",
            )

        at_risk = impacts  

        situation_label = (
            f"a total outage at {supplier_name} (no known delivery date - order "
            f"sized to a standard {OUTAGE_REORDER_TARGET_DAYS}-day reorder target)"
        )
        alternate_allocation, recommended_action = self._build_alternate_allocation(
            supplier_name, at_risk, OUTAGE_REORDER_TARGET_DAYS, situation_label
        )

        reasoning = (
            f"{supplier_name} is experiencing a total outage with no known "
            f"delivery date, affecting {len(impacts)} tank(s). All are treated "
            "as at risk since there is no shipment to wait for."
        )

        return ShipmentDelayResult(
            supplier_name=supplier_name,
            delay_days=None,
            tank_impacts=impacts,
            tanks_at_risk=[i.tank_id for i in at_risk],
            recommended_action=recommended_action,
            alternate_allocation=alternate_allocation,
            reasoning=reasoning,
        )


shipment_delay_agent = ShipmentDelayAgent()