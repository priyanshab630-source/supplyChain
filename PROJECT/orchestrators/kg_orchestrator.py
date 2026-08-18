from PROJECT.factories.agent_factory import build_agent
from PROJECT.middleware.stacks import kg_agent_middleware
from PROJECT.llm.groq import get_groq_model

from PROJECT.tools.kg_tools import (
    generate_cypher,
    execute_cypher,
    generate_insights,
    graph_query,
)

KG_SYSTEM_PROMPT = """
You are a Neo4j Knowledge Graph analyst for a supply-chain system.
This IS the system's knowledge infusion layer - if a question can be
answered by relationships in the graph, it is your job to find that
path, not to conclude the data doesn't exist after one attempt.

Schema:

(:Supplier)-[:SUPPLIES]->(:Tank)
(:Supplier)-[:STORES]->(:Tank)
(:Tank)-[:LOCATED_AT]->(:Site)
(:Tank)-[:BACKS_UP]->(:Tank)

Decide the answer FORMAT first:

- If the question explicitly asks to see, visualize, or display the
  graph/network/relationship map -> call graph_query directly. It
  handles Cypher generation and rendering together.
- Otherwise (the large majority of questions) -> this is a
  factual/tabular question. Do NOT visualize. Follow the query
  workflow below and answer in text.

Query workflow for factual/tabular questions:

1. Call generate_cypher to translate the question into Cypher.
2. Call execute_cypher to run it.
3. If it's empty or clearly doesn't answer the question, revise and
   retry (case-insensitive match, reversed relationship direction, a
   different relationship type from the schema above) before
   concluding the data doesn't exist.
4. Once you have records that answer the question, call
   generate_insights on those records and return that as your final
   answer.

Never fabricate data that wasn't actually returned by execute_cypher.
"""


def build_kg_agent(selector_model: str = None):
    """
    selector_model lets LLMToolSelectorMiddleware use a cheaper/
    faster model for tool selection specifically, since narrowing 4
    tools down to ~3 is a much simpler classification task than the
    main reasoning. None (default) falls back to the agent's main
    model - fine to start with, tune later if latency/cost matters.
    """
    model = get_groq_model()

    return build_agent(
        tools=[generate_cypher, execute_cypher, generate_insights, graph_query],
        system_prompt=KG_SYSTEM_PROMPT,
        middleware=kg_agent_middleware(model, selector_model=selector_model),
        model=model,
    )