from typing import Optional

from langgraph.graph import MessagesState

from PROJECT.models.inventory_models import InventoryResult
from PROJECT.models.consumption_forecast_models import ConsumptionForecastResult
from PROJECT.models.supplier_models import SupplierResult
from PROJECT.models.kg_models import KGResult
from PROJECT.models.risk_models import RiskResult
from PROJECT.models.recommendation_models import Recommendation
from PROJECT.models.malfunction_models import MalfunctionResult
from PROJECT.models.allocation_models import AllocationResult, SupplierAllocationLine
from PROJECT.models.shipment_models import ShipmentDelayResult


class SupplyChainState(MessagesState):

    question: str
    tank_id: Optional[str]
    supplier_name: Optional[str]

    inventory: Optional[InventoryResult]
    forecast: Optional[ConsumptionForecastResult]
    supplier: Optional[SupplierResult]
    kg: Optional[KGResult]
    risk: Optional[RiskResult]
    recommendation: Optional[Recommendation]
    shipment_delay: Optional[ShipmentDelayResult]
    network_results: Optional[list[dict]]
    network_scope: Optional[str]
    # P2: result of MalfunctionAgent.report_malfunction() - which
    # tank failed, which tank backed it up, the surge applied, and
    # whether an emergency delivery is needed.
    malfunction: Optional[MalfunctionResult]
    
    # P3: result of AllocationAgent.allocate() - how much of a gas
    # each contracted supplier should provide for the current demand.
    allocation: Optional[AllocationResult]
    final_answer: Optional[str]

    errors: list[str]

    required_agents: list[str]
    completed_agents: list[str]
    next_agent: str
