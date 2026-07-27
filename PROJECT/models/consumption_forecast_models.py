from pydantic import BaseModel


class ConsumptionForecastResult(BaseModel):

    tank_id: str
    current_inventory: float
    avg_daily_consumption: float
    avg_7_day_consumption: float
    avg_30_day_consumption: float
    forecast_next_day: float
    forecast_next_week: float
    predicted_stockout_date: str | None