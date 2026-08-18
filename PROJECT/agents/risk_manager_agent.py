from PROJECT.models.risk_models import RiskResult
from PROJECT.state.agent_state import SupplyChainState
from PROJECT.models.inventory_models import InventoryResult
from PROJECT.models.consumption_forecast_models import ConsumptionForecastResult
from PROJECT.models.supplier_models import SupplierResult
from PROJECT.models.kg_models import KGResult
from langsmith import traceable

class RiskAgent:

    def __init__(self):
        pass

    # Inventory risk
    def calculate_inventory_risk(self, inventory):
        score = 0
        if inventory is None:
            return score

        if inventory.risk_level == "CRITICAL":
            score += 60
            return score

        elif inventory.risk_level == "HIGH":
            score += 40
            return score

        elif inventory.risk_level == "MEDIUM":
            score += 20
            return score

        return score

    
    # Forecast risk
    def calculate_forecast_risk(self, forecast):
        score = 0
        if forecast is None:
            return score

        if forecast.forecast_next_day > forecast.current_inventory:
            score += 30
            return score

        # if forecast.predicted_consumption > forecast.current_inventory:
        #     return 30

        return score

    # Supplier risk
    def calculate_supplier_risk(self, supplier):
        score = 0
        if supplier is None:
            return score

        if supplier.risk_level == "HIGH":
            score += 20
            return score

        elif supplier.risk_level == "MEDIUM":
            score += 10
            return score

        elif supplier.risk_level == "LOW":
            score += 5
            return score
        
        return score

    # KG risk
    def calculate_kg_risk(self, kg):
            score = 0
            if kg is None:
                return score

            suppliers = []
            for row in kg.records:
                node = row.get("n", {})
                if "name" in node:
                    suppliers.append(node["name"])

            suppliers = list(set(suppliers))
            if len(suppliers) <= 1:
                score += 30

            return score

    # Overall risk
    def calculate_total_risk(self,inventory,forecast,supplier,kg):
        score = (self.calculate_inventory_risk(inventory) + self.calculate_forecast_risk(forecast) + self.calculate_supplier_risk(supplier) + self.calculate_kg_risk(kg))

        return min(max(score, 0), 100)

    # Risk Level
    def calculate_risk_level(self, score, has_any_data):
        if not has_any_data:
            return "UNKNOWN"

        if score >= 80:
            return "CRITICAL"

        elif score >= 60:
            return "HIGH"

        elif score >= 40:
            return "MEDIUM"

        return "LOW"

    @staticmethod
    def can_handle(state):
        return (state.inventory is not None or state.forecast is not None or state.supplier is not None or state.kg is not None)

    def resolve_tank_id(self, state, inventory, forecast, supplier, kg):
        if inventory is not None:
            return inventory.tank_id

        if forecast is not None:
            return forecast.tank_id

        pre_extracted = state.get("tank_id")
        if pre_extracted:
            return pre_extracted

        return "UNKNOWN"

    # Main Workflow
    @traceable(name="RiskAgent.run", run_type="chain")
    def run(self, state):
        print("Running Risk Manager Agent...")
        inventory_data = state.get("inventory")
        forecast_data = state.get("forecast")
        supplier_data = state.get("supplier")
        kg_data = state.get("kg")

        inventory = (
            InventoryResult(**inventory_data)
            if isinstance(inventory_data, dict)
            else inventory_data
        )

        forecast = (
            ConsumptionForecastResult(**forecast_data)
            if isinstance(forecast_data, dict)
            else forecast_data
        )

        supplier = (
            SupplierResult(**supplier_data)
            if isinstance(supplier_data, dict)
            else supplier_data
        )

        kg = (
            KGResult(**kg_data)
            if isinstance(kg_data, dict)
            else kg_data
        )

        has_any_data = any(x is not None
            for x in (inventory, forecast, supplier, kg)
        )

        total_score = self.calculate_total_risk(inventory,forecast,supplier,kg)
        risk_level = self.calculate_risk_level(total_score, has_any_data)
        tank_id = self.resolve_tank_id(state,inventory,forecast,supplier,kg)
        result = RiskResult(
            tank_id=tank_id,
            inventory_risk_score=self.calculate_inventory_risk(inventory),
            forecast_risk_score=self.calculate_forecast_risk(forecast),
            supplier_risk_score=self.calculate_supplier_risk(supplier),
            kg_risk_score=self.calculate_kg_risk(kg),
            overall_risk_score=total_score,
            overall_risk_level=risk_level,
        )

        return result

    