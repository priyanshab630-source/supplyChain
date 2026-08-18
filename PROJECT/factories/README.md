# PROJECT/factories/

## Why this exists
One place that knows how to build a `create_agent` tool-calling
sub-agent, so every orchestrator (`orchestrators/*.py`) calls the same
function instead of each hand-rolling its own `create_agent(...)`
call with slightly different defaults.

## Files & Functions
| File | Function | What it does |
|---|---|---|
| `agent_factory.py` | `default_middleware(model=None)` | The production-hardening middleware every agent gets unless overridden: `SummarizationMiddleware` (trigger at 20 messages, keep last 10), `ToolRetryMiddleware` (2 retries), `ToolCallLimitMiddleware` (max 8 per run, continues past the limit), `ModelCallLimitMiddleware` (max 8 per run, ends the run at the limit). |
| | `AgentOrchestrator` | Thin wrapper class around `create_agent()`. `__init__(system_prompt, tools, middleware=None, model=None)` — accepts a pre-built `model` to avoid constructing a second `ChatGroq` client when a caller already built one (see `middleware/stacks.py`'s comment on why this matters). `.run(question)` invokes the agent with a single `HumanMessage` and returns `{"messages": [...]}`. |
| | `build_agent(system_prompt, tools, middleware=None, model=None)` | The actual function every `orchestrators/*.py` file calls — just constructs and returns an `AgentOrchestrator`. |

## Relationship to `middleware/`
`default_middleware()` here is the LangChain-prebuilt half of the
stack; `middleware/stacks.py`'s `tank_agent_middleware()` /
`supplier_agent_middleware()` / `kg_agent_middleware()` compose THIS
with the custom guardrail/normalization/audit middleware, per agent
type. This file doesn't know about guardrails at all — that
separation is intentional.
