# PROJECT/simulator/

## Why this exists
P5. Lets you inject an event (a tank failing, a shipment delaying, a
supplier going dark) directly, without needing a live telemetry feed
or typing a question — then automatically runs the REAL pipeline on a
natural follow-up question, so you see the whole chain react
end-to-end in one command. Calls the exact same functions a real
trigger would (`malfunction_agent.report_malfunction()`,
`shipment_delay_agent.report_delay()`/`report_outage()`) — no
parallel simulation logic that could drift out of sync with the real
agents.

## Files & Functions
| File | Function | What it does |
|---|---|---|
| `event_simulator.py` | `simulate_tank_malfunction(tank_id)` | Calls `report_malfunction()`, logs to `event_log`, asks the pipeline about the affected backup tank. |
| | `simulate_tank_recovery(tank_id, backup_tank_id?)` | Auto-resolves the backup via `get_backup_for()` (reads `compensating_for`) if not passed explicitly. |
| | `simulate_shipment_delay(supplier, delay_days, tank_id?)` | Calls `report_delay()`, asks a follow-up about the most at-risk tank. |
| | `simulate_shipment_recovery(supplier, tank_id)` | Calls `clear_shipment_delay()`. |
| | `simulate_supplier_outage(supplier)` | Calls `report_outage()` directly — its own real code path with a sane 14-day reorder target, not `report_delay()` fed an arbitrary huge number. |
| | `_run_pipeline(question)` | Runs `run_graph()` with a fresh `thread_id` and `source="simulator"` (so LangSmith can distinguish these from real questions). |
| | `print_history(limit)` | Prints recent `event_log` entries. |

## Run (from repo root, not from inside `PROJECT/`)
```bash
python -m PROJECT.simulator.event_simulator tank-malfunction "Tank 1"
python -m PROJECT.simulator.event_simulator tank-recovery "Tank 1"
python -m PROJECT.simulator.event_simulator shipment-delay "Supplier A" 5
python -m PROJECT.simulator.event_simulator supplier-outage "Supplier B"
python -m PROJECT.simulator.event_simulator history
```

## ⚠️ Warning
Every `simulate_*` command writes REAL status changes to `tank_status`/
`shipment_status`. Run against a staging/test database — not
production, and not the same DB a real demo or live dashboard is
pointed at.
