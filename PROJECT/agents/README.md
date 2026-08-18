# PROJECT/agents/

## Why this exists
The actual business logic. Every file here is a plain Python class —
**not** a LangChain `Runnable` — that does deterministic math/rules
against pandas DataFrames or Neo4j records. The LLM only gets involved
where a question needs free-text interpretation (KG Cypher generation,
the final synthesized answer); everything else here is regular code
you could unit-test without touching an API key.

This is also why every method here needed `@traceable` added by hand
for LangSmith (see `observability/README.md`) — plain classes are
invisible to LangChain's automatic tracing.

## Files & Key Methods
| File | Class | Key methods | What it does |
|---|---|---|---|
| `inventory_agent.py` | `InventoryAgent` | `run(question)`, `run_for_tank(tank_id)` | Consumption math from `consumption_readings`, days of cover, risk tier, spike detection. `run_for_tank` is the clean-input path (added to mirror `SupplierAgent`); `run` regex-extracts a tank id from free text and delegates to it. |
| `consumption_forecast_agent.py` | `ForecastAgent` | `run(question)`, `run_for_tank(tank_id)` | 7/30-day rolling averages, next-day/next-week projections, predicted stockout date. Same clean-path/free-text split as `InventoryAgent`. |
| `supplier_agent.py` | `SupplierAgent` | `run(question)`, `run_for_supplier(name)`, `get_supplier_for_tank()`, `get_supplier_tanks()` | Reliability score, fill rate, single-source-dependency flag. `run_for_supplier` is the original clean-input path both other agents were later modeled on. |
| `kg_agent.py` | `KGAgent` | `run(question, visualize=None)` | Routes between a deterministic Cypher template (`_run_deterministic`, for simple "everything about Tank X" questions) and the LLM tool-calling path (`_run_llm_agent`) for open-ended questions. |
| `risk_manager_agent.py` | `RiskAgent` | `run(state)`, `calculate_total_risk()` | Combines inventory/forecast/supplier/KG risk scores into one overall level. Reads `state["inventory"]` etc. — has no idea whether those numbers came from a normal tank or a surged one (see `tools/tank_status_tools.py`). |
| `recommendation_agent.py` | `RecommendationAgent` | `run(state)` | Turns risk level into a concrete action, supplier, order quantity, delivery date. `recommend_order_qty` uses a 14-day target-inventory formula — the same pattern `shipment_delay_agent.py` reuses for its own order sizing. |
| `malfunction_agent.py` | `MalfunctionAgent` (P2) | `report_malfunction(tank_id)` | Marks a tank down, finds its backup via Neo4j `BACKS_UP`, activates the backup with a surge multiplier, recalculates its days of cover immediately. |
| `allocation_agent.py` | `AllocationAgent` (P3) | `allocate(gas, qty, unavailable_suppliers)` | Splits an order across contracted suppliers proportionally; redistributes an unavailable supplier's share rather than just shrinking the order. |
| `shipment_delay_agent.py` | `ShipmentDelayAgent` (P4) | `report_delay(supplier, days, tank_id?)`, `report_outage(supplier)` | At-risk detection per tank, sized reallocation via `AllocationAgent`. Delay and outage are separate methods with separate order-sizing targets on purpose — see the file's docstring for why merging them was a real bug. |

## Convention worth knowing
Every "already-know-the-identifier" method is named `run_for_*`
(`run_for_tank`, `run_for_supplier`); every free-text fallback is
plain `run(question)` and internally regex-extracts, then delegates.
If you're calling one of these agents with data you already have
clean (e.g. from `state["tank_id"]`), always prefer `run_for_*` —
routing through `run(question)` with a synthetic sentence is what
originally caused garbled lookups (see `supplier_agent.py`'s
docstrings for the specific history).
