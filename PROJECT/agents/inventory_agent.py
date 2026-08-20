from datetime import datetime, timedelta
import re
from PROJECT.models.inventory_models import InventoryResult
from langsmith import traceable


class InventoryAgent:

    def __init__(self, consumption_df, tank_df):
        self.consumption_df = consumption_df
        self.tank_df = tank_df

    def get_tank_data(self, tank_id):
        return (self.consumption_df[self.consumption_df["tank_id"] == tank_id].sort_values("data_timestamp").copy())

    def get_tank_master(self, tank_id):
        result = self.tank_df[self.tank_df["tank_id"] == tank_id]
        if result.empty:
            return None
        return result.iloc[0]

    def calculate_consumption(self, tank_df):
        tank_df["delta"] = (tank_df["amount"] - tank_df["amount"].shift(1))
        tank_df["consumption"] = (tank_df["delta"].where(tank_df["delta"] < 0).abs())

        return tank_df

    def detect_refill_events(self, tank_df):
        tank_df["shipment"] = (tank_df["delta"].where(tank_df["delta"] > 0))
        return tank_df

    def calculate_avg_consumption(self, tank_df):
        avg_hourly = (tank_df["consumption"].dropna().mean())
        if avg_hourly != avg_hourly:  
            avg_hourly = 0

        avg_daily = avg_hourly * 24

        return {
            "avg_hourly": avg_hourly,
            "avg_daily": avg_daily
        }

    def calculate_days_of_cover(self,inventory,avg_daily):
        if not avg_daily:
            return float("inf")

        return inventory / avg_daily

    def detect_consumption_spike(self, tank_df):
        recent = (tank_df["consumption"].tail(24).mean())
        baseline = (tank_df["consumption"].mean())

        if recent != recent or baseline != baseline:  
            return False

        return recent > (baseline * 1.25)

    def calculate_risk_level(self,inventory,rop,low_alarm, low_low_alarm):
        if rop is None or low_alarm is None or low_low_alarm is None:
            return "UNKNOWN"

        if inventory <= low_low_alarm:
            return "CRITICAL"

        elif inventory <= low_alarm:
            return "HIGH"

        elif inventory <= rop:
            return "MEDIUM"

        return "LOW"

    def calculate_risk_score(self,inventory,days_of_cover,spike_detected):
        score = 0
        if days_of_cover < 3:
            score += 50

        elif days_of_cover < 7:
            score += 25

        if spike_detected:
            score += 25

        return min(score, 100)

    def predict_stockout_date(self,inventory,avg_daily):
        if not avg_daily:
            return None

        days = inventory/avg_daily

        return (datetime.now() + timedelta(days=days)).isoformat()

    def generate_summary(self, risk_level, days_of_cover):

        return (
            f"{risk_level} risk. "
            f"{days_of_cover:.2f} days of cover remaining."
        )

    def extract_tank_id(self, question: str):
        """
        Extract Tank ID from user question.
        Example:
        'Show inventory of Tank 4'
        -> Tank 4
        """

        match = re.search(r"tank\s*(\d+)", question, re.IGNORECASE)

        if match:
            return f"Tank {match.group(1)}"

        return None

    @traceable(name="InventoryAgent.run_for_tank", run_type="chain")
    def run_for_tank(self, tank_id: str):
        """
        Runs the full inventory pipeline for an ALREADY-KNOWN,
        already-normalized tank_id - no regex, no re-parsing a
        sentence. Use this whenever the caller already has a clean
        id (a structured tool arg, or state["tank_id"] from
        nodes.py) instead of routing through run(question), which
        exists only for the free-text fallback case.
        """
        print("Running Inventory Agent...")
 
        tank_master = self.get_tank_master(tank_id)
        if tank_master is None:
            raise ValueError(f"{tank_id} does not exist in the Tank Master.")
 
        tank_df = self.get_tank_data(tank_id)
 
        if tank_df.empty:
            return InventoryResult(
                gas=tank_master["gas"],
                tank_id=tank_id,
                current_inventory=None,
                has_consumption_history=False,
                avg_hourly_consumption=0,
                avg_daily_consumption=0,
                days_of_cover=0,
                spike_detected=False,
                risk_level="UNKNOWN",
                risk_score=0,
                predicted_stockout_date=None,
            )
 
        tank_df = self.calculate_consumption(tank_df)
        tank_df = self.detect_refill_events(tank_df)
        consumption_stats = self.calculate_avg_consumption(tank_df)
        avg_hourly = consumption_stats["avg_hourly"]
        avg_daily = consumption_stats["avg_daily"]
        current_inventory = tank_df.iloc[-1]["amount"]
        days_of_cover = self.calculate_days_of_cover(current_inventory, avg_daily)
        spike_detected = self.detect_consumption_spike(tank_df)
 
        risk_level = self.calculate_risk_level(
            inventory=current_inventory,
            rop=tank_master.get("rop"),
            low_alarm=tank_master.get("low_alarm"),
            low_low_alarm=tank_master.get("low_low_alarm"),
        )
        risk_score = self.calculate_risk_score(
            inventory=current_inventory,
            days_of_cover=days_of_cover,
            spike_detected=spike_detected,
        )
        stockout_date = self.predict_stockout_date(inventory=current_inventory, avg_daily=avg_daily)
 
        return InventoryResult(
            gas=tank_master["gas"],
            tank_id=tank_id,
            has_consumption_history=True,
            current_inventory=current_inventory,
            avg_hourly_consumption=avg_hourly,
            avg_daily_consumption=avg_daily,
            days_of_cover=days_of_cover,
            spike_detected=spike_detected,
            risk_level=risk_level,
            risk_score=risk_score,
            predicted_stockout_date=stockout_date,
        )

    @traceable(name="InventoryAgent.run", run_type="chain")
    def run(self, question: str):
        tank_id = self.extract_tank_id(question)
        if not tank_id:
            raise ValueError("Please specify a tank. Example: 'Show inventory of Tank 4'")
        return self.run_for_tank(tank_id)