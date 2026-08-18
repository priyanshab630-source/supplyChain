# PROJECT/state/

## Why this exists
One shared schema every graph node reads from and writes to. Without
a single source of truth here, nodes would silently disagree on field
names/types and fail in ways that only show up at runtime.

## Files & Functions
| File | Class | What it does |
|---|---|---|
| `agent_state.py` | `SupplyChainState(MessagesState)` | The full graph state: `question`, `tank_id`, `supplier_name` (pre-extracted by regex in `run_graph.py`), one optional result field per agent (`inventory`, `forecast`, `supplier`, `kg`, `risk`, `recommendation`, `network_results`, `malfunction`, `allocation`, `shipment_delay`), `errors` (accumulates across nodes), `required_agents`/`completed_agents`/`next_agent` (the supervisor's routing bookkeeping), and `final_answer`. |

## Note
Every optional result field is typed against a specific Pydantic model
from `PROJECT/models/` — e.g. `inventory: Optional[InventoryResult]`.
Adding a new agent (as P2–P4 did with `malfunction`/`allocation`/
`shipment_delay`) means adding both the field here AND the
corresponding model in `models/`, or LangGraph will accept an
untyped/unchecked value there silently.
