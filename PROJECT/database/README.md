# PROJECT/database/

## Why this exists
The only place raw connection objects get created. Everything else
(`data_loader/`, `agents/`, `guardrails/`) imports from here rather
than constructing its own engine/driver — one connection pool per
process, not one per caller.

## Files & Functions
| File | Function | What it does |
|---|---|---|
| `postgres.py` | `data_engine` | SQLAlchemy engine for domain data (tank/supplier/consumption tables). Reads `DATA_DATABASE_URL`, falling back to `DATABASE_URL`, falling back to `sqlite:///./supply_chain.db`. This is a SEPARATE engine from `backend/database.py`'s (which is chat history) even though they may point at the same physical DB file/instance — different table sets, same underlying storage, by design (see `add_switchover_and_contract_data.py`'s comment: "different tables in one instance"). |
| `neo4j.py` | `get_graph()` | Lazily connects to Neo4j on first use — everything else (FastAPI, the CLI, every non-KG agent) works fine even if Neo4j is down; only questions that actually need the KG agent fail, with a clear error surfaced through `kg_node`'s existing try/except. |

## Credentials
Both files read from environment variables (`.env` in `PROJECT/`).
**Never commit `.env`** — see the root README's setup section for what
needs to be in it.
