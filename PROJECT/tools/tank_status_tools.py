"""
P6: makes tank roles/surge actually affect decisions, without
modifying RiskAgent or RecommendationAgent at all.

The mechanism: apply_surge_adjustment() / apply_forecast_surge_adjustment()
get called on an InventoryResult/ConsumptionForecastResult right
after it's computed, BEFORE it's stored in graph state. RiskAgent and
RecommendationAgent already read state["inventory"] / state["forecast"]
as their input - they have no idea whether those numbers came from a
normal tank or a surged one, and they don't need to. A tank with no
tank_status row (never touched by a malfunction) passes through
unchanged.
"""

from datetime import datetime, timedelta

from PROJECT.data_loader.loader import load_tank_status
from PROJECT.models.inventory_models import InventoryResult
from PROJECT.models.consumption_forecast_models import ConsumptionForecastResult


def get_tank_status_row(tank_id: str):

    status_df = load_tank_status()
    row = status_df.loc[status_df["tank_id"] == tank_id]

    return row.iloc[0].to_dict() if not row.empty else None


def _get_surge_multiplier(tank_id: str) -> float:

    status = get_tank_status_row(tank_id)

    if not status:
        return 1.0

    surge = status.get("surge_multiplier")

    return surge if surge is not None else 1.0


def apply_surge_adjustment(result: InventoryResult) -> InventoryResult:

    surge = _get_surge_multiplier(result.tank_id)

    if surge == 1.0:
        return result

    adjusted = result.model_copy()
    adjusted.avg_daily_consumption = result.avg_daily_consumption * surge
    adjusted.avg_hourly_consumption = result.avg_hourly_consumption * surge

    if adjusted.avg_daily_consumption and result.current_inventory is not None:
        adjusted.days_of_cover = result.current_inventory / adjusted.avg_daily_consumption

    return adjusted


def apply_forecast_surge_adjustment(result: ConsumptionForecastResult) -> ConsumptionForecastResult:

    surge = _get_surge_multiplier(result.tank_id)

    if surge == 1.0:
        return result

    adjusted = result.model_copy()
    adjusted.avg_daily_consumption = result.avg_daily_consumption * surge
    adjusted.avg_7_day_consumption = result.avg_7_day_consumption * surge
    adjusted.avg_30_day_consumption = result.avg_30_day_consumption * surge
    adjusted.forecast_next_day = result.forecast_next_day * surge
    adjusted.forecast_next_week = result.forecast_next_week * surge

    if adjusted.avg_daily_consumption:
        days = result.current_inventory / adjusted.avg_daily_consumption
        adjusted.predicted_stockout_date = (datetime.now() + timedelta(days=days)).isoformat()

    return adjusted
