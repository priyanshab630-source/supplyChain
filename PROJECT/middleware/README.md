# PROJECT/middleware/

## Why this exists
Custom `create_agent` middleware — cross-cutting logic (validation,
normalization, logging) that applies to a tool-calling agent's loop
without being baked into any individual tool or agent's code. Built
alongside LangChain's own prebuilt middleware (`SummarizationMiddleware`,
`ToolRetryMiddleware`, etc. — see `factories/README.md`), not instead
of it.

## Files & Functions
| File | Middleware | Hook type | What it does |
|---|---|---|---|
| `cypher_guardrail_middleware.py` | `cypher_guardrail_middleware` | `wrap_tool_call` | Runs `guardrails/cypher_guardrail.py`'s `validate_cypher()` on any tool call whose args contain a `cypher` field — short-circuits with an error instead of calling the real tool if it's not a safe read-only query. |
| `tank_id_normalizer_middleware.py` | `tank_id_normalizer_middleware` | `wrap_tool_call` | Normalizes any tool call's `tank_id` arg (`"1"` → `"Tank 1"`) automatically, structurally instead of relying on each tool remembering to call `tools/tank_id_utils.py` itself. |
| `question_guardrail_middleware.py` | `question_guardrail_middleware` | `before_agent` | Runs `guardrails/input_guardrail.py`'s `validate_question()` on the latest human message before the agent does anything — defense in depth alongside the pipeline-level check in `backend/graph_stream.py`. |
| `tool_call_audit_middleware.py` | `tool_call_audit_middleware` | `wrap_tool_call` | Logs every tool call (name, args, duration, success/failure) to `event_log` via `data_loader/loader.py`'s `write_event_log()` — a persisted, SQL-queryable record that complements LangSmith rather than replacing it. |
| `stacks.py` | `tank_agent_middleware()`, `supplier_agent_middleware()`, `kg_agent_middleware()` | — | Composes the four middlewares above with `factories/agent_factory.py`'s `default_middleware()`, per agent type. This is the one place that decides "what does the KG agent get that the inventory agent doesn't" — see `orchestrators/README.md`'s table. |

## Verification note
`create_agent`'s middleware system is a comparatively new LangChain
API. Before trusting any of this in production, confirm
`request.tool_call`'s exact shape against your installed version:
```bash
pip show langchain langchain-core
python -c "from langchain.agents.middleware import wrap_tool_call, before_agent, LLMToolSelectorMiddleware; print('OK')"
```
