# PROJECT/scripts/

## Why this exists
One-off or maintenance scripts you run manually from the command
line — not imported by the running application. Distinct from
`data_loader/`'s seed scripts in that these operate on Neo4j
specifically, after the Postgres-side data is already in place.

## Files & Functions
| File | Function | What it does |
|---|---|---|
| `seed_backs_up_relationships.py` | `run()` | Reads `tank_master.switchover_group` and creates `BACKS_UP` relationships in Neo4j between every pair of tanks sharing a group (bidirectional). This is what `malfunction_agent.py`'s Neo4j query and `eval/scenarios.py`'s `generate_kg_backup_scenarios()` both depend on existing. |

## Run order
Must run AFTER `data_loader/add_switchover_and_contract_data.py` (which
populates `switchover_group`) and AFTER your Tank nodes already exist
in Neo4j:
```bash
python -m PROJECT.data_loader.add_switchover_and_contract_data
python -m PROJECT.scripts.seed_backs_up_relationships
```

## Note
`kg_ablation.py` (in `graph/`) calls this script's `run()` function
directly (`reseed_backs_up`) to restore relationships after its own
A/B test removes them for the control condition — you don't need to
re-run this manually after running the ablation.
