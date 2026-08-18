# frontend/src/

## Why this exists
The actual application code, split by concern: `api/` talks to the
backend, `hooks/` owns state/streaming logic, `components/` renders
UI. `App.jsx` is the only file that ties them together.

## Folders
| Folder | Purpose |
|---|---|
| `api/` | HTTP/SSE calls to the backend — see `api/README.md` |
| `hooks/` | React state + streaming logic — see `hooks/README.md` |
| `components/` | UI rendering — see `components/README.md` |

## Files & Functions
| File | Function/Component | What it does |
|---|---|---|
| `App.jsx` | `App` | Root component. Creates a thread on mount (`createThread()`), shows a loading state until `threadId` resolves, then renders `ChatWindow`. **Known gap**: the `createThread().then(setThreadId)` call has no `.catch()` — a failed request (backend down, CORS, bad `VITE_API_BASE`) fails silently and the UI hangs on "Starting conversation..." forever. Fix is documented in this conversation's early messages — add error state + a `.catch()` here before shipping. |

## Data flow (one question, start to finish)
```
App.jsx (mount)
  → api/client.js: createThread()
  → ChatWindow.jsx renders
User types a question
  → hooks/useChatStream.js: ask()
  → api/client.js: askQuestion() — opens the SSE stream
  → one onEvent(nodeName, payload) call per graph node
  → components/AgentFlow.jsx + ResultPanel.jsx re-render live
  → final_answer event → MessageBubble.jsx adds the assistant's reply
```
