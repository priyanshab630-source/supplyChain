from typing import Optional
from pydantic import BaseModel

class InventoryResult(BaseModel):

    gas: str
    tank_id: str
    current_inventory: Optional[float] = None
    avg_hourly_consumption: Optional[float] = None
    avg_daily_consumption: Optional[float] = None
    days_of_cover: Optional[float] = None
    spike_detected: bool = False
    risk_level: str
    risk_score: float = 0
    predicted_stockout_date: Optional[str] = None
    has_consumption_history: bool = True

