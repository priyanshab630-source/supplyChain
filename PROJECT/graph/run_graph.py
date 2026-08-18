import re

from langchain_core.messages import HumanMessage
from langgraph.graph.message import add_messages

from PROJECT.graph.workflow import graph
from PROJECT.guardrails.input_guardrail import validate_question
from PROJECT.observability.tracing import build_run_config


def extract_tank_id(question: str):

    match = re.search(r"tank\s*(\d+)", question, re.IGNORECASE)

    if match:
        return f"Tank {match.group(1)}"

    return None


def extract_supplier_name(question: str):
    """
    Requires the token immediately after "supplier" to start with an
    uppercase letter and contain no spaces - matches the dataset's
    actual naming convention (Supplier A, Supplier B, ...) and
    naturally excludes ordinary sentence words that happen to follow
    "supplier".
    """

    match = re.search(r"(?i:supplier)\s+([A-Z][A-Za-z0-9]*)", question)

    if match:
        return f"Supplier {match.group(1)}"

    return None


def run_graph(question: str, thread_id: str = "default", source: str = "cli"):
    """
    thread_id identifies the conversation. Pass the SAME thread_id
    across multiple calls to keep them in one conversation.
    `source` is passed through to LangSmith's run tags (see
    observability/tracing.py) - defaults to "cli" for direct
    invocation; the P5 simulator passes source="simulator" so its
    runs are distinguishable from real questions in the LangSmith UI.
    """
    
    validate_question(question)
    config = build_run_config(thread_id, question, source=source)


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
        "network_scope": None,
        "malfunction": None,
        "allocation": None,
        "shipment_delay": None,
        "risk": None,
        "recommendation": None,
        "final_answer": None,
        "errors": [],
        "required_agents": [],
        "completed_agents": [],
        "next_agent": "supervisor",
    }


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
