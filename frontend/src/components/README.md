# frontend/src/components/

## Why this exists
Pure rendering, driven entirely by state from `hooks/useChatStream.js`.
None of these components fetch data themselves.

## Files & Functions
| File | Component | What it does |
|---|---|---|
| `ChatWindow.jsx` | `ChatWindow` | Top-level chat UI. Owns the message list and input box locally (`useState`); delegates streaming to `useChatStream`. On submit: appends the user message immediately, clears input, calls `ask(question)`. On `answer` changing (via `useEffect`), appends the assistant message. |
| `AgentFlow.jsx` | `AgentFlow` | Renders one row per entry in `AGENT_ORDER`, colored by status: pending (not reached yet), done, or error (`_hasOwnError`). This is the live "which node is running now" indicator. |
| `ResultPanel.jsx` | `ResultPanel` | Renders the raw JSON payload of every completed node except `final_answer` (that one becomes a chat bubble instead) — useful for seeing exactly what each agent returned, not just the synthesized answer. |
| `MessageBubble.jsx` | `MessageBubble` | One chat bubble, styled by `role` (`user` vs `assistant`). |

## Rendering order in ChatWindow
```
messages (bubbles)
AgentFlow (only shown while loading OR flow has entries)
ResultPanel (only shown once flow has entries)
input form
```
