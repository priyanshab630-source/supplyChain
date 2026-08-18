# PROJECT/observability/

## Why this exists
One place that builds the `config` dict passed to `graph.stream()`,
so every entry point (FastAPI, CLI, simulator) tags its LangSmith
traces consistently instead of four ad-hoc dicts that happen to agree
today and drift apart later.

## Files & Functions
| File | Function | What it does |
|---|---|---|
| `tracing.py` | `build_run_config(thread_id, question, source, extra_tags)` | Builds `{"configurable": {"thread_id": ...}, "metadata": {...}, "tags": [f"source:{source}"], "run_name": "..."}`. `source` is what lets you filter LangSmith runs by origin: `"api"` (real requests via `backend/graph_stream.py`), `"cli"` (`run_graph.py` invoked directly), `"simulator"` (P5's follow-up questions). |

## What this does NOT do
Doesn't wrap or configure LangChain/LangGraph's automatic tracing
itself — that's controlled entirely by environment variables
(`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`),
which must be set for tracing to happen at all. This module only adds
consistent tagging on top of tracing that's already active.

## The other half of tracing (not in this folder)
Plain-Python agent classes in `agents/` aren't LangChain `Runnable`s,
so calls into them are invisible in the trace tree without a manual
`@traceable` decorator from the `langsmith` package on each key
method. That's applied directly in each `agents/*.py` file, not here
— see the file-by-file list in `agents/README.md`.
