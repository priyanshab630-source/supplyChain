import ast
import json
import re
from langchain_core.messages import AIMessage, ToolMessage
from PROJECT.models.kg_models import KGResult
from PROJECT.tools.kg_tools import (
    execute_cypher,
    generate_insights,
    graph_query,
    build_tank_cypher,
    generate_cypher,
    visualize_subgraph
)
from PROJECT.orchestrators.kg_orchestrator import build_kg_agent
from langsmith import traceable


VISUALIZE_KEYWORDS = [
    "visualize",
    "visualise",
    "show graph",
    "show the graph",
    "display network",
    "relationship map",
    "graph structure",
    "draw graph",
    "plot graph",
]


def _last_tool_message(messages, tool_name):
    for message in reversed(messages):
        if isinstance(message, ToolMessage) and getattr(message, "name", None) == tool_name:
            return message

    return None


def _parse_tool_payload(content):
    """
    ToolMessage content for a tool that returns something other than
    a plain string usually comes back as a stringified Python repr
    (not JSON). Try JSON first, then a literal-eval fallback, and
    give up gracefully rather than crashing the whole KG turn.
    """

    if isinstance(content, (list, dict)):
        return content

    if not isinstance(content, str):
        return content

    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        return ast.literal_eval(content)
    except (ValueError, SyntaxError):
        pass

    return content

class KGAgent:

    def __init__(self):
        self._llm_agent = build_kg_agent()

    def extract_tank_id(self, question):
        match = re.search(r"tank\s*(\d+)", question, re.IGNORECASE)
        if match:
            return f"Tank {match.group(1)}"

        return None


    @staticmethod
    def wants_visualization(question: str) -> bool:
        q = question.lower()

        return any(k in q for k in VISUALIZE_KEYWORDS)

    @traceable(name="KGAgent.run_deterministic", run_type="chain")
    def _run_deterministic(self, question, tank_id, visualize):
        cypher = build_tank_cypher(tank_id)
        records = execute_cypher.invoke({"cypher": cypher})

        insights = generate_insights.invoke({
            "records": records,
            "question": question,
        })

        graph_path = None
        should_visualize = (
            visualize
            if visualize is not None
            else self.wants_visualization(question)
        )

        if should_visualize:
            graph_path = visualize_subgraph.invoke({"cypher": cypher})

        return KGResult(
            question=tank_id,
            cypher_query=cypher,
            records=records,
            insights=insights,
            graph_path=graph_path
        )

    @traceable(name="KGAgent.run_llm_agent", run_type="chain")
    def _run_llm_agent(self, question):
        agent_output = self._llm_agent.run(question)
        messages = agent_output.get("messages", [])

        cypher_msg = _last_tool_message(messages, "generate_cypher")
        cypher_query = cypher_msg.content if cypher_msg else ""

        records_msg = _last_tool_message(messages, "execute_cypher")
        records = _parse_tool_payload(records_msg.content) if records_msg else []

        if not isinstance(records, list):
            records = []

        insights_msg = _last_tool_message(messages, "generate_insights")
        if insights_msg:
            insights = insights_msg.content

        else:
            final_ai = next((
                    m for m in reversed(messages)
                    if isinstance(m, AIMessage) and m.content
                ),
                None,)

            insights = (final_ai.content
                if final_ai
                else "No insights could be generated for this question."
            )

        graph_msg = (_last_tool_message(messages, "graph_query") or _last_tool_message(messages, "visualize_subgraph"))
        graph_path = graph_msg.content if graph_msg else None

        return KGResult(
            question=question,
            cypher_query=cypher_query,
            records=records,
            insights=insights,
            graph_path=graph_path,
        )

    @traceable(name="KGAgent.run", run_type="chain")
    def run(self,question: str,visualize: bool = None):
        print("Running Knowledge Graph Agent...")
        tank_id = self.extract_tank_id(question)

        if tank_id:
            return self._run_deterministic(question, tank_id, visualize)

        return self._run_llm_agent(question)


kg_agent = KGAgent()