from typing import Optional, List

from pydantic import BaseModel

from PROJECT.models.allocation_models import AllocationResult


class TankDelayImpact(BaseModel):
    tank_id: str
    days_of_cover: Optional[float] = None
    will_stockout_before_delivery: Optional[bool] = None
    error: Optional[str] = None


class ShipmentDelayResult(BaseModel):
    supplier_name: str
    delay_days: Optional[int] = None  
    tank_impacts: List[TankDelayImpact]
    tanks_at_risk: List[str]
    recommended_action: str
    alternate_allocation: Optional[AllocationResult] = None
    reasoning: str