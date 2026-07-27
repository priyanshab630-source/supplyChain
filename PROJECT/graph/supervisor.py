from typing import Dict
from langchain_core.messages import AIMessage
from PROJECT.graph.planner import build_plan
from PROJECT.state.agent_state import SupplyChainState

def supervisor_node(state: SupplyChainState) -> Dict:

    print("\n" + "=" * 80)
    print("SUPERVISOR")
    print("=" * 80)

    question = state["question"]

    required_agents = list(
        state.get("required_agents", [])
    )

    completed_agents = list(
        state.get("completed_agents", [])
    )

    if not required_agents:
        required_agents = build_plan(question)

    print("\nExecution Plan")
    print(required_agents)

    print("\nCompleted")
    print(completed_agents)

    next_agent = "end"

    for agent in required_agents:
        if agent not in completed_agents:
            next_agent = agent
            break

    print("\nNext Agent :", next_agent)

    return {
        "messages": [
            AIMessage(
                content=f"Supervisor selected {next_agent}"
            )
        ],

        "required_agents": required_agents,
        "completed_agents": completed_agents,
        "next_agent": next_agent,
    }