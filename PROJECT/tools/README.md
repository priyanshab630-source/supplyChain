# PROJECT/tools/

## Why this exists
LangChain `@tool`-wrapped functions — the only things the LLM
tool-calling sub-agents (built in `orchestrators/`) can actually call.
Every tool here is a thin wrapper around an `agents/` class: parse/
normalize the LLM's structured args, call the real logic, return a
plain dict (`result.model_dump(mode="json")` or `{"error": ...}`).

## Files & Functions
| File | Tool/Function | What it does |
|---|---|---|
| `inventory_tools.py` | `inventory_risk_tool` (args: `InventoryLookupArgs`) | Structured single-field arg (`tank_id`), normalizes it, calls `InventoryAgent.run_for_tank()`. |
| `consumption_forcast_tools.py` | `forecast_tool` (args: `ForecastLookupArgs`) | Same pattern, calls `ForecastAgent.run_for_tank()`. |
| `supplier_tools.py` | `supplier_tool` (args: `SupplierLookupArgs`) | Two optional fields (`supplier_name` OR `tank_id`) — this file is the original pattern the other two were rebuilt to match. Resolves a tank to its supplier first if only `tank_id` is given. |
| `kg_tools.py` | `generate_cypher`, `execute_cypher`, `generate_insights`, `visualize_subgraph`, `graph_query`, `build_tank_cypher` | The KG toolset. `generate_cypher` is LLM output; `execute_cypher`/`visualize_subgraph` both run `validate_cypher()` (from `guardrails/`) before touching Neo4j — this is the fix for the Cypher-injection gap found during this build. `build_tank_cypher` is the deterministic template for simple tank-lookup questions, bypassing the LLM entirely. |
| `tank_id_utils.py` | `normalize_tank_id()` | Shared helper (`"1"` → `"Tank 1"`) — was duplicated inline in two tool files before being extracted here. |
| `tank_status_tools.py` | `apply_surge_adjustment()`, `apply_forecast_surge_adjustment()` | **The P6 mechanism.** Called inside `graph/nodes.py`'s `inventory_node`/`forecast_node` right after computing a result, before it's stored in state — this is the single hook that makes tank roles/surge affect `RiskAgent` and `RecommendationAgent` with zero changes to either of those files. |

## Why tools are separate from agents
An `agents/*.py` class can be called two ways: directly with a clean
argument (`run_for_tank("Tank 1")`, used by `graph/nodes.py` for the
deterministic path), or via an LLM tool call (used when no tank_id
was pre-extracted from the question, and the LLM has to figure out
what's being asked). `tools/` exists only for the second path — it's
the LLM-facing surface, not the logic itself.
