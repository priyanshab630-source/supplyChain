# frontend/src/api/

## Why this exists
The only file allowed to know the backend's URL shape and response
formats. Every component/hook goes through here — nothing else in
`src/` calls `fetch()` directly.

## Files & Functions
| File | Function | What it does |
|---|---|---|
| `client.js` | `createThread()` | `POST /threads`, returns the new `thread_id`. **No error handling** — see `src/README.md`'s known gap. |
| | `fetchHistory(threadId)` | `GET /threads/{id}/history`, returns past messages + agent runs. |
| | `askQuestion(threadId, question, onEvent)` | `POST /ask`, reads the response body as an SSE stream manually (splits on `\n\n`, parses `event:`/`data:` lines), calls `onEvent(nodeName, payload)` once per node. This is hand-rolled SSE parsing, not `EventSource` — needed because `EventSource` can't send a POST body, and `/ask` requires one (`{thread_id, question}`). |

## Config
`API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api"`
— set `VITE_API_BASE` in `frontend/.env` to point elsewhere (staging,
a different port, etc).
