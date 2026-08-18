from datetime import datetime, timedelta

from langsmith import traceable

from PROJECT.models.recommendation_models import Recommendation
from PROJECT.models.inventory_models import InventoryResult
from PROJECT.models.risk_models import RiskResult
from PROJECT.models.supplier_models import SupplierResult



class RecommendationAgent:

    def __init__(self):
        pass

    def recommend_action(self, risk_level):
        if risk_level == "CRITICAL":
            return "Emergency Reorder"

        elif risk_level == "HIGH":
            return "Place Replenishment Order"

        elif risk_level == "MEDIUM":
            return "Monitor Inventory"

        elif risk_level == "UNKNOWN":
            return "Insufficient Data - Unable to Recommend"

        return "No Action Required"

    def recommend_supplier(self, supplier):
        if supplier is None:
            return None

        return supplier.supplier_name

    def recommend_order_qty(self, inventory):
        if inventory is None:
            return 0

        if not inventory.has_consumption_history:
            return 0

        target_days = 14
        target_inventory = (inventory.avg_daily_consumption * target_days)
        qty = (target_inventory - inventory.current_inventory)
        return max(qty, 0)

    def recommend_delivery_date(self, risk_level):
        if risk_level == "CRITICAL":
            return (datetime.now() + timedelta(days=1)).isoformat()

        elif risk_level == "HIGH":
            return (datetime.now() + timedelta(days=3)).isoformat()

        return (datetime.now() + timedelta(days=7)).isoformat()

    def generate_reasoning(self, inventory, risk):
        risk_level = (risk.overall_risk_level
            if risk is not None
            else "UNKNOWN"
        )

        if risk_level == "UNKNOWN":
            return ("Not enough data was available to assess risk ""or generate a confident recommendation for this tank.")

        if inventory is None:
            return ( f"{risk_level} risk. " "Inventory data unavailable for this tank." )

        if not inventory.has_consumption_history:
            return ( f"{risk_level} risk. " "No consumption history available for this tank.")

        return ( f"{risk_level} risk. " f"{inventory.days_of_cover:.2f} days of cover remaining.")

    def resolve_tank_id(self, state, inventory, risk):
        if inventory is not None:
            return inventory.tank_id

        if risk is not None and risk.tank_id:
            return risk.tank_id

        pre_extracted = state.get("tank_id")
        if pre_extracted:
            return pre_extracted

        return "UNKNOWN"

    @traceable(name="RecommendationAgent.run", run_type="chain")
    def run(self, state):
        print("Running Recommendation Agent...")
        inventory = state.get("inventory")
        supplier = state.get("supplier")
        risk = state.get("risk")
        if isinstance(inventory, dict):
            inventory = InventoryResult(**inventory)

        if isinstance(supplier, dict):
            supplier = SupplierResult(**supplier)

        if isinstance(risk, dict):
            risk = RiskResult(**risk)

        risk_level = (risk.overall_risk_level
            if risk is not None
            else "UNKNOWN"
        )

        action = self.recommend_action(risk_level)
        supplier_name = self.recommend_supplier(supplier)
        qty = self.recommend_order_qty(inventory)
        delivery = self.recommend_delivery_date(risk_level)
        reasoning = self.generate_reasoning(inventory,risk)
        tank_id = self.resolve_tank_id(state,inventory,risk)

        recommendation = Recommendation(
            tank_id=tank_id,
            recommended_action=action,
            recommended_supplier=supplier_name,
            recommended_order_qty=qty,
            recommended_delivery_date=delivery,
            priority=risk_level,
            reasoning=reasoning,
        )

        return recommendation
