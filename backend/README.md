# backend/

## Why this exists
The FastAPI service that sits between the frontend and the LangGraph
pipeline in `PROJECT/`. It owns HTTP concerns only — routing, request/
response shapes, streaming, and its own persistence tables (chat
history). It does not contain any agent logic; every question is
handed off to `PROJECT/graph/run_graph.py`'s compiled graph.

## Folders
| Folder | Purpose |
|---|---|
| `routers/` | FastAPI route definitions — see `routers/README.md` |
| `data/` | *(sibling to backend, not inside it — see repo root)* |

## Files & Functions
| File | Function/Class | What it does |
|---|---|---|
| `main.py` | `app` (FastAPI instance) | Wires CORS (`localhost:5173` only), registers `chat_router` and `admin_router`, runs `init_db()` on startup, exposes `GET /health`. |
| `database.py` | `init_db()` | Creates SQLModel tables (`Thread`, `Message`, `AgentRun`) if they don't exist. |
| | `get_session()` | FastAPI dependency — yields a SQLModel `Session`, one per request. |
| `db_models.py` | `Thread` | One row per conversation (`id`, `created_at`). |
| | `Message` | One row per chat turn — user question or assistant answer. |
| | `AgentRun` | One row per graph node that fires during a run — what lets `/threads/{id}/history` replay a past turn's full flow, not just the final answer. |
| `schemas.py` | `AskRequest`, `NewThreadResponse` | Pydantic request/response shapes for the API. |
| `persistence.py` | `ensure_thread()` | Creates a `Thread` row if one doesn't exist yet for this `thread_id`. |
| | `save_message()` | Writes one `Message` row (role + content). |
| | `save_agent_run()` | Writes one `AgentRun` row (node name + its output). |
| | `get_thread_history()` | Reads back every `Message` and `AgentRun` for a thread, ordered by time. |
| `graph_stream.py` | `stream_graph_events()` | The actual bridge to `PROJECT/`: builds the graph's initial state, runs `graph.stream()`, yields one SSE event per node, and persists each result via `persistence.py`. This is where the input guardrail and LangSmith `build_run_config()` are wired in. |

## What's NOT here
Domain logic (inventory math, risk scoring, agent orchestration) lives
entirely in `PROJECT/`. If you're debugging *why an answer is wrong*,
you're in the wrong folder — start in `PROJECT/graph/nodes.py`. If
you're debugging *the API not responding, CORS, or persistence*, this
is the right folder.
