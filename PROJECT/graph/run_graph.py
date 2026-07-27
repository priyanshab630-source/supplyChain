import re
from langchain_core.messages import HumanMessage
from langgraph.graph.message import add_messages
from PROJECT.graph.workflow import graph

def extract_tank_id(question: str):
    match = re.search(r"tank\s*(\d+)", question, re.IGNORECASE)
    if match:
        return f"Tank {match.group(1)}"

    return None


def extract_supplier_name(question: str):

    match = re.search(r"supplier\s+([A-Za-z0-9][A-Za-z0-9\s]*?)(?:[.?!]|$)", question, re.IGNORECASE)

    if match:
        return f"Supplier {match.group(1).strip()}"

    return None


def run_graph(question: str, thread_id: str = "default"):
    """
    thread_id identifies the conversation. Pass the SAME thread_id
    across multiple calls to keep them in one conversation (the
    checkpointer on `graph` persists state per thread_id, so
    `messages` accumulates instead of starting over each call).
    Use a fresh thread_id to start an unrelated conversation.
    """

    initial_state = {
        "messages": [
            HumanMessage(content=question)
        ],
        "question": question,
        "tank_id": extract_tank_id(question),
        "supplier_name": extract_supplier_name(question),
        "inventory": None,
        "forecast": None,
        "supplier": None,
        "kg": None,
        "network_results": None,
        "risk": None,
        "recommendation": None,
        "final_answer": None,
        "errors": [],
        "required_agents": [],
        "completed_agents": [],
        "next_agent": "supervisor",
    }

    config = {"configurable": {"thread_id": thread_id}}
    accumulated_state = dict(initial_state)

    for event in graph.stream(initial_state, config=config):

        print("=" * 80)
        print(event)
        for node_name, node_output in event.items():
            if not isinstance(node_output, dict):
                continue
            for key, value in node_output.items():
                if key == "messages":
                    accumulated_state["messages"] = add_messages(
                        accumulated_state.get("messages", []),
                        value,
                    )
                else:
                    accumulated_state[key] = value

    return accumulated_state
