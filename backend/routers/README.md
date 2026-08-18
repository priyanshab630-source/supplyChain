# backend/routers/

## Why this exists
Keeps FastAPI route definitions separate from the app setup
(`main.py`) and the actual chat/persistence logic (`graph_stream.py`,
`persistence.py`). Each file here is a thin HTTP layer — parse the
request, call into the real logic, shape the response.

## Files & Functions
| File | Route | What it does |
|---|---|---|
| `chat.py` | `POST /api/threads` | Creates a new conversation (`new_thread()`), returns a fresh `thread_id`. |
| | `POST /api/ask` | The main endpoint (`ask()`) — takes `{thread_id, question}`, returns a `StreamingResponse` (SSE) backed by `graph_stream.stream_graph_events()`. |
| | `GET /api/threads/{thread_id}/history` | Returns every persisted message and agent run for a thread (`history()`). |
| `admin.py` | `POST /api/admin/refresh-data` | Clears the in-process data cache (`refresh_all()` in `PROJECT/data_loader/loader.py`) so the next request re-reads from the DB instead of stale startup-time values. Call this after re-running `seed_from_csv.py` or editing tables directly — no server restart needed. |

## Notes
- `chat.py`'s `/ask` is the only route that touches the LangGraph
  pipeline — everything else is thin CRUD around the chat-history
  tables.
- `admin.py`'s refresh endpoint exists because `PROJECT/data_loader/loader.py`
  caches DataFrames in-process (`_cache = {}`) for performance. If you
  update the database directly and answers still look stale, hit this
  endpoint before assuming something's broken.
