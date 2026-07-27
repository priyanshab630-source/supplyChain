from typing import Optional

from langgraph.graph import MessagesState

from PROJECT.models.inventory_models import InventoryResult
from PROJECT.models.consumption_forecast_models import ConsumptionForecastResult
from PROJECT.models.supplier_models import SupplierResult
from PROJECT.models.kg_models import KGResult
from PROJECT.models.risk_models import RiskResult
from PROJECT.models.recommendation_models import Recommendation


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
    network_results: Optional[list[dict]]
    network_scope: Optional[str]
    final_answer: Optional[str]

    errors: list[str]

    required_agents: list[str]
    completed_agents: list[str]
    next_agent: str
