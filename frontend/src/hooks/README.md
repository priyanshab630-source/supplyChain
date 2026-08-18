# frontend/src/hooks/

## Why this exists
Owns the streaming state machine — turning a raw sequence of SSE
events into "which nodes have run, did any of them error, what's the
final answer" — so components stay dumb (pure rendering, no stream
logic).

## Files & Functions
| File | Export | What it does |
|---|---|---|
| `useChatStream.js` | `AGENT_ORDER` | The fixed display order of nodes in `AgentFlow.jsx`: `inventory, forecast, supplier, kg, network, risk, recommendation, final_answer`. **Not automatically kept in sync** with `PROJECT/graph/workflow.py` — if you add a new node there (e.g. `malfunction`, `allocation`, `shipment_delay` from P2–P4), add it here too or it won't show in the UI's progress list even though it ran. |
| | `useChatStream(threadId)` | Returns `{ flow, answer, loading, ask }`. `ask(question)` calls `askQuestion()` from `api/client.js`, and on each event: stores the node's payload in `flow`, tracks whether this node introduced a NEW error (`_hasOwnError`, compared against a running `seenErrorCount`), and sets `answer` once `final_answer` arrives. |

## Note on error tracking
`_hasOwnError` only flags a node if `payload.errors.length` grew
*since the last node* — this is what lets `AgentFlow.jsx` show a red
dot on the specific node that introduced a problem, not every node
downstream of it (since `errors` accumulates in graph state and every
later node's payload would otherwise also show a non-empty list).
