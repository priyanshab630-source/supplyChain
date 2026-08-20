"""
LangSmith tracing helpers.

Assumes LANGCHAIN_TRACING_V2 / LANGCHAIN_API_KEY / LANGCHAIN_PROJECT
are already set in your environment. Once those are set, real
LangChain/LangGraph constructs (graph.stream, chain.invoke, @tool
calls) trace automatically - no code changes needed for those.

What this module adds on top:

1. build_run_config() - the ONE place that builds the `config` dict
   passed to graph.stream(). Every entry point (the FastAPI /ask
   endpoint, run_graph.py's CLI path, the P5 simulator) now calls
   this instead of building its own ad-hoc config dict, so tracing
   metadata/tags stay consistent instead of four call sites that
   happen to agree today and quietly drift apart later.

2. Nothing else lives here on purpose. The @traceable decorators on
   the plain-Python agent classes (InventoryAgent.run, RiskAgent.run,
   MalfunctionAgent.report_malfunction, etc.) are added directly in
   those files via `from langsmith import traceable`, since those
   classes aren't LangChain Runnables - without the decorator, calls
   into them are invisible gaps in the trace tree: you'd see the
   graph NODE's span (inventory_node, risk_node, ...) but nothing of
   what happened inside the agent it called. See
   LANGSMITH_CHECKLIST.md for the full list of where to add it.
"""


def build_run_config(thread_id: str, question: str = None, source: str = "api", extra_tags=None) -> dict:
    """
    `source` is what lets you filter runs in the LangSmith UI by
    where they came from, instead of guessing from thread_id naming
    conventions:
      - "api"       a real request through FastAPI's /ask endpoint
      - "cli"       run_graph.py invoked directly
      - "simulator" the P5 event simulator's follow-up questions
    """

    tags = [f"source:{source}"]
    if extra_tags:
        tags.extend(extra_tags)

    metadata = {"thread_id": thread_id}
    if question:
        metadata["question"] = question

    config = {
        "configurable": {"thread_id": thread_id},
        "metadata": metadata,
        "tags": tags,
    }

    if question:
        config["run_name"] = f"{source}: {question[:60]}"

    return config