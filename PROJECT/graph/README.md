# PROJECT/graph/

## Why this exists
The actual LangGraph `StateGraph` — every node, how they route to
each other, and the persistence layer that lets a conversation survive
a process restart. This is the orchestration layer; it calls into
`agents/` for the real work.

## Files & Functions
| File | Key contents | What it does |
|---|---|---|
| `workflow.py` | `graph` (compiled) | Registers every node (`supervisor`, `inventory`, `forecast`, `supplier`, `kg`, `network`, `risk`, `recommendation`, `malfunction`, `allocation`, `shipment_delay`, `final_answer`), wires conditional edges via `router.py`, compiles with a persistent checkpointer from `checkpointer.py`. |
| `nodes.py` | One `*_node(state)` function per node | Each node: calls the relevant agent (deterministic path if `state["tank_id"]`/`state["supplier_name"]` is set, else the LLM orchestrator fallback), wraps the call in `try/except`, updates `completed_agents`/`errors`, returns `next_agent: "supervisor"`. `final_answer_node` and `recommendation_node` also run the output/recommendation guardrails here. |
| `supervisor.py` | `supervisor_node(state)` | Calls `planner.build_plan()` once per conversation turn to decide which agents this question needs, then picks the next incomplete one from that plan each time it's re-entered. |
| `planner.py` | `build_plan(question)`, `VALID_AGENTS` | LLM call that returns an ordered list of agent names to run. Validates output against `VALID_AGENTS`, de-duplicates, and force-inserts `risk` before `recommendation` if `recommendation` was requested without it. |
| `router.py` | `router(state)` | Reads `state["next_agent"]` and returns it as the LangGraph routing key — the actual conditional-edge function every node points to. |
| `run_graph.py` | `run_graph(question, thread_id, source)`, `extract_tank_id()`, `extract_supplier_name()` | The non-streaming entry point (used by the CLI, the simulator, `kg_ablation.py`). Pre-extracts `tank_id`/`supplier_name` via regex before the graph even starts — this is what lets deterministic nodes skip the LLM orchestrator fallback entirely for simple questions. |
| `checkpointer.py` | `get_checkpointer()` | **The memory fix.** Auto-picks a persistent LangGraph checkpointer (`SqliteSaver` or `PostgresSaver`) based on `DATABASE_URL`, replacing `InMemorySaver()` — which lost every in-flight conversation on process restart. |
| `prompts.py` | `PLANNER_PROMPT`, `FINAL_ANSWER_PROMPT` | The two LLM prompts used outside individual agents — plan generation and final answer synthesis. |
| `kg_ablation.py` | `run_ablation()` | Not part of the main pipeline — a standalone A/B test comparing KG answer quality with vs. without `BACKS_UP` graph relationships seeded. Scenarios sourced from `eval/scenarios.py`'s `generate_kg_backup_scenarios()`. |

## Request lifecycle, one level of detail deeper than `PROJECT/README.md`
```
run_graph() / graph_stream.py
  → START → supervisor_node (builds/advances the plan)
  → router() picks the next agent by name
  → that node runs, calls its agent, writes results + completed_agents
  → back to supervisor_node
  → ...repeats until plan is exhausted...
  → router() returns "final_answer"
  → final_answer_node synthesizes everything into prose (+ guardrails)
  → END
```
