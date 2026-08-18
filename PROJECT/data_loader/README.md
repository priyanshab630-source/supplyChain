# PROJECT/data_loader/

## Why this exists
Two different kinds of data live behind this folder, and it's worth
keeping the distinction clear:
- **Reference data** (`tank_master`, `supplier_info`, `consumption_readings`,
  `supplier_schedule`, `supplier_contract_shares`) — read-heavy,
  cached in-process, refreshed only when explicitly told to.
- **Live operational state** (`tank_status`, `shipment_status`,
  `event_log`, `eval_results`) — write-heavy, one row per tank/supplier/
  event, no caching (always `force_refresh=True` reads), because this
  data changes mid-conversation (a malfunction, a delay) and stale
  reads here would silently undo P2/P4/P6's whole point.

## Files & Functions
| File | Function | What it does |
|---|---|---|
| `loader.py` | `load_tank_master_data()`, `load_info_data()`, `load_consumption_data()`, `load_schedule_data()` | Cached reference-data reads (`_load()` internally, `_cache = {}`). |
| | `refresh_all()` | Clears the whole cache — call after re-seeding or editing tables directly (also exposed via `backend/routers/admin.py`'s `/refresh-data`). |
| | `load_tank_status()` / `write_tank_status()` / `get_backup_for()` | P2/P6 — live per-tank status, surge multiplier, and `compensating_for` (which failed tank this one is backing up — what lets P5's `tank-recovery` auto-resolve without `--backup`). |
| | `load_shipment_status()` / `write_shipment_status()` / `clear_shipment_delay()` | P4 — live per-(supplier, tank) delay/outage status. |
| | `load_event_log()` / `write_event_log()` | P5/audit — append-only event history (simulated events, tool-call audit logs, guardrail warnings). |
| | `load_eval_results()` / `write_eval_run()` | P8 — persisted eval run summaries, comparable over time. |
| `init_tank_status.py` | `run()` | One-time seed: populates `tank_status` from `tank_master.default_role`, so ONLINE/STANDBY/ALWAYS_ONLINE is visible from day one instead of only after the first malfunction touches a tank. |
| `seed_from_csv.py` | `seed()` | Loads your static CSVs (`data/*.csv`) into the DB tables `loader.py` reads from. Run once, or whenever a CSV is replaced. |
| `add_switchover_and_contract_data.py` | `run()` | P0 scaffolding: adds `switchover_group`/`default_role` to `tank_master` and generates `supplier_contract_shares` — currently DUMMY values, replace once real data is available (P7). |

## Run order (fresh database)
```bash
python -m PROJECT.data_loader.seed_from_csv
python -m PROJECT.data_loader.add_switchover_and_contract_data
python -m PROJECT.data_loader.init_tank_status
python -m PROJECT.scripts.seed_backs_up_relationships   # see scripts/README.md
```
