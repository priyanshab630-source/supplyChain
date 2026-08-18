from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from langgraph.checkpoint.memory import InMemorySaver

from PROJECT.state.agent_state import SupplyChainState

from PROJECT.graph.nodes import (
    inventory_node,
    forecast_node,
    supplier_node,
    kg_node,
    network_node,
    malfunction_node,
    allocation_node,
    shipment_delay_node,
    risk_node,
    recommendation_node,
    final_answer_node,
)

from PROJECT.graph.supervisor import supervisor_node
from PROJECT.graph.router import router


builder = StateGraph(SupplyChainState)


builder.add_node("supervisor", supervisor_node)
builder.add_node("inventory", inventory_node)
builder.add_node("forecast", forecast_node)
builder.add_node("supplier", supplier_node)
builder.add_node("kg", kg_node)
builder.add_node("network", network_node)
builder.add_node("malfunction", malfunction_node)
builder.add_node("allocation", allocation_node)
builder.add_node("risk", risk_node)
builder.add_node("recommendation", recommendation_node)
builder.add_node("final_answer", final_answer_node)
builder.add_node("shipment_delay", shipment_delay_node)


builder.add_edge(START, "supervisor")


ROUTES = {
    "inventory": "inventory",
    "forecast": "forecast",
    "supplier": "supplier",
    "kg": "kg",
    "network": "network",
    "malfunction": "malfunction",
    "allocation": "allocation",
    "shipment_delay": "shipment_delay",
    "risk": "risk",
    "recommendation": "recommendation",
    "final_answer": "final_answer",
}

builder.add_conditional_edges("supervisor", router, ROUTES)


for worker in [
    "inventory",
    "forecast",
    "supplier",
    "kg",
    "network",
    "malfunction",
    "allocation",
    "shipment_delay",
    "risk",
    "recommendation",
]:

    builder.add_conditional_edges(
        worker,
        router,
        {**ROUTES, "supervisor": "supervisor"},
    )


builder.add_edge("final_answer", END)


checkpointer = InMemorySaver()

graph = builder.compile(
    name="SupplyChainSupervisor",
    checkpointer=checkpointer,
)
