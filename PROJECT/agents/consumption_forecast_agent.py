from datetime import datetime, timedelta
import re
from PROJECT.models.consumption_forecast_models import ConsumptionForecastResult
from langsmith import traceable


class ForecastAgent:

    def __init__(self, consumption_df):
        self.consumption_df = consumption_df

    def get_tank_history(self, tank_id):
        return (self.consumption_df[self.consumption_df["tank_id"] == tank_id].sort_values("data_timestamp").copy())

    def calculate_consumption(self, tank_df):
        tank_df["delta"] = (tank_df["amount"] - tank_df["amount"].shift(1))
        tank_df["consumption"] = (tank_df["delta"].where(tank_df["delta"] < 0).abs())

        return tank_df

    def calculate_avg_daily_consumption(self, tank_df):
        avg_hourly = (tank_df["consumption"].dropna().mean())

        if avg_hourly != avg_hourly:  
            avg_hourly = 0

        return avg_hourly * 24

    def calculate_7_day_avg(self, tank_df):
        last_7_days = (tank_df["consumption"].dropna().tail(24 * 7))

        if len(last_7_days) == 0:
            return 0

        return last_7_days.mean() * 24

    def calculate_30_day_avg(self, tank_df):
        last_30_days = (tank_df["consumption"].dropna().tail(24 * 30))

        if len(last_30_days) == 0:
            return 0

        return last_30_days.mean() * 24

    def forecast_next_day_consumption(self,tank_df):
        return self.calculate_7_day_avg(tank_df)

    def forecast_next_week_consumption(self,tank_df):
        daily_forecast = (self.calculate_7_day_avg(tank_df))
        return daily_forecast * 7

    def forecast_inventory_curve(self,inventory,daily_consumption,days=7):
        curve = []
        for day in range(days + 1):
            projected_inventory = (inventory - (daily_consumption * day))
            curve.append(
                {
                    "day": day,
                    "inventory": max(projected_inventory,0)
                }
            )

        return curve

    def predict_stockout_date(self,inventory,daily_consumption):
        if not daily_consumption:
            return None
        
        days = (inventory/daily_consumption)

        return (datetime.now() + timedelta(days=days)).isoformat()


    def extract_tank_id(self, question):
        match = re.search(r"tank\s*(\d+)", question, re.IGNORECASE)

        if match:
            return f"Tank {match.group(1)}"

        return None
    
    @traceable(name="ForecastAgent.run_for_tank", run_type="chain")
    def run_for_tank(self, tank_id: str):
        print("Running Forecast Agent...")
 
        tank_df = self.get_tank_history(tank_id)
 
        if tank_df.empty:
            raise ValueError(
                f"No consumption history found for {tank_id}. "
                "A forecast cannot be generated without historical data."
            )
 
        tank_df = self.calculate_consumption(tank_df)
        current_inventory = tank_df.iloc[-1]["amount"]
        avg_daily = self.calculate_avg_daily_consumption(tank_df)
        avg_7_day = self.calculate_7_day_avg(tank_df)
        avg_30_day = self.calculate_30_day_avg(tank_df)
        next_day_forecast = self.forecast_next_day_consumption(tank_df)
        next_week_forecast = self.forecast_next_week_consumption(tank_df)
        stockout_date = self.predict_stockout_date(current_inventory, avg_daily)
 
        return ConsumptionForecastResult(
            tank_id=tank_id,
            current_inventory=current_inventory,
            avg_daily_consumption=avg_daily,
            avg_7_day_consumption=avg_7_day,
            avg_30_day_consumption=avg_30_day,
            forecast_next_day=next_day_forecast,
            forecast_next_week=next_week_forecast,
            predicted_stockout_date=stockout_date,
        )

    @traceable(name="ForecastAgent.run", run_type="chain")
    def run(self, question: str):
        tank_id = self.extract_tank_id(question)
        if not tank_id:
            raise ValueError("Please specify a tank. Example: 'Show consumption forecast for Tank 4'")
        return self.run_for_tank(tank_id)