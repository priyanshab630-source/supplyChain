import json

from langchain_core.messages import HumanMessage

from PROJECT.graph.workflow import graph
from PROJECT.graph.run_graph import extract_tank_id, extract_supplier_name

from sqlmodel import Session

from backend import persistence


def _build_initial_state(question: str) -> dict:

    return {
        "messages": [HumanMessage(content=question)],
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


def _serialize(value):
    """Pydantic result models -> plain JSON-able dicts; everything else passes through."""

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    return value


def _sse(event_name: str, payload: dict) -> str:

    return f"event: {event_name}\ndata: {json.dumps(payload, default=str)}\n\n"


def stream_graph_events(question: str, thread_id: str, session: Session):
    """
    Runs the graph for one question and yields one SSE message per
    node as it completes - inventory, forecast, supplier, kg,
    network, risk, recommendation, final_answer. Each event is also
    written to Postgres so the turn can be replayed later via
    /threads/{id}/history.
    """

    initial_state = _build_initial_state(question)
    config = {"configurable": {"thread_id": thread_id}}

    persistence.save_message(session, thread_id, "user", question)

    for event in graph.stream(initial_state, config=config):

        for node_name, node_output in event.items():

            if not isinstance(node_output, dict):
                continue

            payload = {
                key: _serialize(value)
                for key, value in node_output.items()
                if key != "messages"
            }

            persistence.save_agent_run(session, thread_id, node_name, payload)

            yield _sse(node_name, payload)

            if node_name == "final_answer" and node_output.get("final_answer"):
                persistence.save_message(session, thread_id, "assistant", node_output["final_answer"])