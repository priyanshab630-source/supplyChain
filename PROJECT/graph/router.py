from typing import Literal

from PROJECT.state.agent_state import SupplyChainState


def router(state: SupplyChainState) -> Literal[
    "supervisor",
    "inventory",
    "forecast",
    "supplier",
    "kg",
    "risk",
    "recommendation",
    "network",
    "malfunction",
    "allocation",
    "shipment_delay",
    "final_answer",
]:

    next_agent = state["next_agent"]
    print(f"\nRouting -> {next_agent}")
    if next_agent == "end":
        return "final_answer"

    return next_agent
