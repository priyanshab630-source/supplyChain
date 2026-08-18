from typing import Optional, List

from pydantic import BaseModel

from PROJECT.models.allocation_models import AllocationResult


class TankDelayImpact(BaseModel):
    """
    Per-tank read of what a specific shipment delay means for that
    tank: how many days of cover it has left (at its CURRENT/surged
    consumption rate - see tools/tank_status_tools.py's
    apply_surge_adjustment, which already ran before this is built,
    so a tank mid-malfunction-surge is correctly judged against its
    elevated burn rate, not its normal one) versus how long the
    delayed shipment will now take to arrive.
    """

    tank_id: str
    days_of_cover: Optional[float] = None
    will_stockout_before_delivery: Optional[bool] = None
    error: Optional[str] = None


class ShipmentDelayResult(BaseModel):
    """
    Full picture for one delay event: every tank the delayed
    supplier feeds (or just the one named tank, if the question
    specified one), which of those are actually at risk, and what to
    do about it - either "monitor, nothing at risk" or a concrete
    reallocation plan built by reusing AllocationAgent's
    unavailable-supplier redistribution path (P3), treating the
    delayed supplier the same way P3 treats a supplier that can't
    fulfill its share at all.
    """

    supplier_name: str
    delay_days: Optional[int] = None  # None = indefinite outage (report_outage), not a numeric delay
    tank_impacts: List[TankDelayImpact]
    tanks_at_risk: List[str]
    recommended_action: str
    alternate_allocation: Optional[AllocationResult] = None
    reasoning: str