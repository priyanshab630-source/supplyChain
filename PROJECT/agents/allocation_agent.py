"""
P3: Supplier schedule allocation.

Given a gas and a total quantity that needs to be ordered, splits it
across the suppliers who serve that gas, proportional to their
contract_share (from supplier_contract_shares, seeded by
data_loader/add_switchover_and_contract_data.py - currently dummy
equal shares until real contract percentages are available).

Handles the "one supplier can't fulfill its share" case via
unavailable_suppliers: their share is redistributed proportionally
across the remaining suppliers, not just dropped (which would silently
under-order the gas).
"""

import pandas as pd
from langsmith import traceable
from PROJECT.database.postgres import data_engine
from PROJECT.models.allocation_models import AllocationResult, SupplierAllocationLine

@traceable
class AllocationAgent:

    def _load_contract_shares(self, gas: str) -> pd.DataFrame:
        shares_df = pd.read_sql_table("supplier_contract_shares", data_engine)
        return shares_df[shares_df["gas"] == gas].copy()

    @traceable(name="AllocationAgent.allocate", run_type="chain")
    def allocate(self, gas: str, total_qty_needed: float, unavailable_suppliers: list = None,) -> AllocationResult:
        unavailable_suppliers = unavailable_suppliers or []
        shares_df = self._load_contract_shares(gas)

        if shares_df.empty:
            raise ValueError(
                f"No contracted suppliers found for gas '{gas}'. Check "
                "supplier_contract_shares (run "
                "add_switchover_and_contract_data.py if it's missing)."
            )

        available_df = shares_df[~shares_df["supplier_name"].isin(unavailable_suppliers)].copy()
        if available_df.empty:
            raise ValueError(
                f"All contracted suppliers for '{gas}' are unavailable "
                f"({', '.join(unavailable_suppliers)}) - no allocation is possible."
            )

        total_available_share = available_df["contract_share"].sum()
        available_df["normalized_share"] = available_df["contract_share"] / total_available_share

        lines = []

        for _, row in available_df.iterrows():
            allocated_qty = total_qty_needed * row["normalized_share"]
            lines.append(
                SupplierAllocationLine(
                    supplier_name=row["supplier_name"],
                    contract_share=row["contract_share"],
                    allocated_qty=allocated_qty,
                    allocated_share_actual=row["normalized_share"],
                )
            )

        lines.sort(key=lambda line: -line.allocated_qty)

        reasoning_parts = [
            f"Allocated {total_qty_needed:,.0f} units of {gas} across "
            f"{len(lines)} supplier(s), proportional to contracted share."
        ]

        if unavailable_suppliers:
            reasoning_parts.append(
                f"{', '.join(unavailable_suppliers)} excluded as unavailable; "
                "their share was redistributed to the remaining supplier(s) "
                "rather than simply reducing the total order."
            )

        return AllocationResult(
            gas=gas,
            total_qty_needed=total_qty_needed,
            allocations=lines,
            reasoning=" ".join(reasoning_parts),
        )

allocation_agent = AllocationAgent()
