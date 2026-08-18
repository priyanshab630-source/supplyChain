from typing import Optional

from pydantic import BaseModel


class MalfunctionResult(BaseModel):

    failed_tank_id: str
    backup_tank_id: Optional[str] = None
    backup_activated: bool = False
    surge_multiplier_applied: Optional[float] = None
    adjusted_days_of_cover: Optional[float] = None
    emergency_delivery_needed: bool = False
    reasoning: str
