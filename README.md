# Supply Chain Multi-Agent System

A LangGraph-based multi-agent assistant for gas-tank supply chain operations: inventory
health, consumption forecasting, supplier reliability, knowledge-graph relationships
(Neo4j), risk scoring, and reorder recommendations — all orchestrated by an LLM
supervisor/planner, with a FastAPI + SSE backend and a React frontend.


---

## Architecture at a glance

```
frontend (React)  --SSE-->  backend (FastAPI)  --LangGraph-->  PROJECT/graph (supervisor)
                                    |                                |
                              Postgres/SQLite                agents/tools/orchestrators
                            (chat + domain data)                     |
                                                                Neo4j (relationships)
```

- **Planner/Supervisor loop** (`PROJECT/graph`): an LLM decides which of
  `inventory / forecast / supplier / kg / risk / recommendation / network` agents a
  question needs, then the supervisor dispatches them one at a time until the plan is
  done, then synthesizes a final answer.
- **Deterministic-first design**: whenever a tank id or supplier name can be
  regex-extracted from the question, nodes call the plain-Python agent classes directly
  (fast, reproducible, no LLM cost/variance). LLM tool-agents are a fallback for
  free-text questions only.
- **Streaming**: every node's output streams to the frontend as an SSE event and is
  persisted per-thread, so a conversation's full agent trace can be replayed later.

---

## Repository layout

```
PROJECT/
  agents/          deterministic business-logic engines (inventory, forecast, supplier, kg, risk, recommendation)
  models/          pydantic result schemas
  orchestrators/   builds the LLM fallback agent per domain
  tools/           @tool wrappers + shared data-loading per domain
  state/           SupplyChainState (LangGraph state shape)
  graph/           planner, supervisor, router, nodes, prompts, workflow, run_graph, ablation
  factories/       shared agent-building helper
  database/        Neo4j + Postgres connections
  data_loader/     CSV seeding, cached table loaders, dummy switchover/contract data
  scripts/         one-off maintenance scripts (BACKS_UP relationship seeding)

backend/
  main.py, database.py, db_models.py, schemas.py, persistence.py, graph_stream.py
  routers/         admin.py, chat.py

frontend/
  src/api/         client.js (fetch + SSE parsing)
  src/hooks/        useChatStream.js
  src/components/   ChatWindow, AgentFlow, ResultPanel, MessageBubble
  src/App.jsx
```

---

## Getting started

```bash
# 1. Seed domain data from CSVs into the DB (first run, or whenever a CSV changes)
python -m PROJECT.data_loader.seed_from_csv

# 2. (Optional, once) generate dummy switchover/contract metadata
python -m PROJECT.data_loader.add_switchover_and_contract_data

# 3. (Optional, once) seed BACKS_UP relationships into Neo4j
python -m PROJECT.scripts.seed_backs_up_relationships

# 4. Run the backend
uvicorn backend.main:app --reload

# 5. Run the frontend
cd frontend && npm run dev
```

After changing underlying tables directly (or re-running `seed_from_csv.py`), call
`POST /api/admin/refresh-data` instead of restarting the server — it clears the
in-process pandas cache in `PROJECT/data_loader/loader.py`.

---

## Known gaps / rough edges worth fixing soon

These aren't blockers, but they're small enough to knock out early and will save
confusion later:

- **`PROJECT/factories/agent_factory.py`** — the content pasted for this file was
  actually a duplicate of `workflow.py`. The real factory (`build_agent`) is used by all
  four orchestrators and should be reviewed/documented properly.
- **`SupplierAgent.calculate_fill_rate` and `calculate_supplier_reliability`** currently
  compute the exact same thing (completed ÷ total shipments). Worth deciding whether
  reliability should eventually diverge (e.g. weight by on-time delivery, not just
  presence of a quantity) or just collapse into one method.
- **`RiskAgent.calculate_forecast_risk`** has a commented-out alternate branch
  (`predicted_consumption > current_inventory`) that was never wired up — decide whether
  to remove it or finish it.
- **`frontend/src/App.jsx`** — the pasted source is missing a closing brace/parenthesis
  on the final `return`; confirm the real file compiles.
- **`ResultPanel.jsx`** renders raw `JSON.stringify` dumps for every node's payload —
  fine for debugging, but worth designing real per-agent cards (inventory gauge,
  forecast chart, supplier scorecard, network ranking table) before this ships to
  non-technical users.
- **`kg_ablation.py`** is explicitly a *starting* harness: `SCENARIOS` is written
  against dummy switchover pairings, and scoring is a simple substring-match on the
  expected tank id. Don't treat its output as a real result yet.
- **Reliability duplication aside**, several `risk_level` buckets across agents
  (inventory, supplier, overall risk) use independent hard-coded thresholds — worth
  centralizing if these need to be tuned together later.

---

## Roadmap (near-term)

This is derived directly from the project's own status tracker
(see the "Business Requirement" table in `PROJECT_DOCUMENTATION.md §15`). Ordered
by dependency, matching the "Suggested Order to Build" already agreed:

| # | Feature | Depends on | Status |
|---|---|---|---|
| 1 | **Dynamic event simulator** — manually (or via a small script) flip a tank's status in Postgres to simulate a malfunction, shipment delay, or supplier outage, and re-run the agent pipeline against the new state. | Nothing | ❌ Not started |
| 2 | **Tank malfunction handling** — detect `status == MALFUNCTION`, look up the backup tank via the `BACKS_UP` relationship in Neo4j, flip the backup to `ONLINE`, and trigger downstream recalculation. | #1 + existing `BACKS_UP` relationships | ❌ Not started |
| 3 | **Consumption recalculation on failover** — once a backup tank goes online, increase its consumption rate (the surviving tank now does the work of two) and re-run inventory/forecast for it. | #2 | ❌ Not started |
| 4 | **Emergency delivery recommendation** — if failover consumption pushes days-of-cover below a threshold, recommend an emergency shipment (extends `RecommendationAgent`). | #3 | ❌ Not started |
| 5 | **Shipment delay handling** — detect a delayed shipment from the schedule data, estimate whether inventory runs out before it arrives, and recommend pulling in an earlier shipment or switching supplier. | #4 (shares the emergency-delivery logic path) | ❌ Not started |
| 6 | **Supplier schedule allocation algorithm** — use the (currently dummy, equal-split) `supplier_contract_shares` table to decide how much gas to order from each supplier while respecting contract percentages, including the case where one supplier can't fulfill its share. | `supplier_contract_shares` table (already generated) | 🟡 Data ready, no algorithm yet |
| 7 | **Replace dummy switchover/contract data with real Intel data** | Data availability from Intel | ⏳ Waiting — no code changes should be needed once available, only regenerating the tables |
| 8 | **Wire ONLINE/STANDBY/ALWAYS_ONLINE roles into decisions** — `risk_manager_agent.py` and `recommendation_agent.py` currently ignore `default_role`/`switchover_group` entirely; a standby tank sitting idle should probably not be scored/recommended the same way as an online one. | #2, #6 | 🟡 Data stored, unused |
| 9 | **Expand the KG ablation study** — replace dummy `SCENARIOS` with real questions/expected answers once real switchover data lands, add more test cases per gas type, and consider swapping the substring-match scorer for something like RAGAS faithfulness/answer-relevancy. | #7 | 🟡 Basic version done, needs real data |

### Smaller near-term polish (can happen in parallel, not gated on the above)

- Fix the known gaps listed above (factory file, duplicate reliability method, dead
  `RiskAgent` branch, `App.jsx`).
- Replace `ResultPanel.jsx`'s raw JSON dump with per-agent UI cards.
- Consider centralizing risk-level thresholds (inventory/supplier/overall) into one
  config so they can be tuned consistently.
- Add automated tests around the regex extractors (`extract_tank_id`,
  `extract_supplier_name`/`extract_supplier`) — these are load-bearing for the entire
  deterministic-fast-path design, and are exactly the kind of thing that silently
  regresses when someone tweaks a prompt or a CSV format.

---

## Data flow notes for future contributors

- Domain data (tank master, supplier info, consumption, schedule) lives in Postgres (or
  local SQLite by default), loaded once and cached in-process by
  `PROJECT/data_loader/loader.py`. **Call `POST /api/admin/refresh-data`** (not a
  restart) after changing the underlying tables.
- Relationship data (Supplier→Tank, Tank→Site, Tank→Tank `BACKS_UP`) lives in Neo4j,
  queried through `PROJECT/database/neo4j.py`'s lazy `get_graph()` singleton.
- Chat/run history lives in the backend's own Postgres/SQLite tables
  (`backend/db_models.py`) — by default this is the *same* database instance as the
  domain data, just different tables, unless `DATABASE_URL`/`DATA_DATABASE_URL` are set
  to point elsewhere.
