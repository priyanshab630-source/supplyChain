# PROJECT/orchestrators/

## Why this exists
Each file here builds ONE tool-calling sub-agent: a system prompt +
its tool(s) + a middleware stack, via `factories/agent_factory.py`'s
`build_agent()`. These are only invoked as the free-text fallback path
— when `graph/nodes.py` couldn't pre-extract a clean `tank_id`/
`supplier_name` from the question and has to let an LLM figure out
what tool to call and with what arguments.

## Files & Functions
| File | Function | Tools given | Middleware stack |
|---|---|---|---|
| `inventory_orchestrator.py` | `build_inventory_agent()` | `inventory_risk_tool` | `tank_agent_middleware` |
| `consumption_orchestrator.py` | `build_forecast_agent()` | `forecast_tool` | `tank_agent_middleware` |
| `supplier_orchestrator.py` | `build_supplier_agent()` | `supplier_tool` | `supplier_agent_middleware` |
| `kg_orchestrator.py` | `build_kg_agent(selector_model?)` | `generate_cypher`, `execute_cypher`, `generate_insights`, `graph_query` | `kg_agent_middleware` — the only stack with `LLMToolSelectorMiddleware` (narrows 4 tools to ~3 per question) and the Cypher guardrail, since this is the only orchestrator that touches Neo4j |

All four call `get_groq_model()` once and pass the SAME model instance
into both `build_agent(..., model=model)` and their middleware stack
builder, so `SummarizationMiddleware` and the actual agent share one
client instead of two.

## Where these are actually used
`graph/nodes.py` builds all four at module level (`inventory_agent =
build_inventory_agent()`, etc.) and only calls `.run(question)` on
them when `state.get("tank_id")`/`state.get("supplier_name")` is
empty — i.e., these are the "the deterministic shortcut didn't apply"
path, not the primary one.
