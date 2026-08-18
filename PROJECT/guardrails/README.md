# PROJECT/guardrails/

## Why this exists
Plain-Python validation logic, deliberately dependency-free (no
guardrails-ai, no NeMo) so it's fully auditable and matches the rest
of this codebase's style. `middleware/` wraps these as `create_agent`
hooks; `graph/nodes.py` and `graph_stream.py` call them directly at
node/entry-point boundaries. Same functions, two different call
sites, so protection doesn't depend on which code path a question
happens to take.

## Files & Functions
| File | Function | Blocks | Hard/Soft |
|---|---|---|---|
| `exceptions.py` | `GuardrailViolation` | — | The one exception type every guardrail raises. Plain `Exception` subclass on purpose — every node's existing `try/except Exception` already catches it with zero new error-handling code needed anywhere. |
| `cypher_guardrail.py` | `validate_cypher(cypher)` | Any generated Cypher that isn't a single-statement, read-only `MATCH...RETURN` | **Hard** |
| `input_guardrail.py` | `validate_question(question)` | Empty input, >2000 chars, known prompt-injection phrasings | **Hard** |
| `output_guardrail.py` | `check_for_leakage(answer)`, `find_ungrounded_tank_ids(answer, known_ids)` | Secrets/stack traces in the final answer (hard); "Tank N" mentions that don't exist in `tank_master` (soft — logged, not blocked) | **Both** |
| `recommendation_guardrail.py` | `validate_recommendation(recommendation)` | Any `recommended_action` outside the known 5-value set | **Hard** |

## Why the tank-id check is soft
If someone asks about "Tank 99" and it doesn't exist, the *correct*
answer mentions "Tank 99" while saying it doesn't exist. Hard-blocking
that would turn a correct answer into an error — log it, watch how
often it fires on real questions, tighten later if warranted.

## What this doesn't cover
Not a jailbreak classifier (`input_guardrail.py` is a fixed pattern
list). Doesn't validate Cypher *correctness*, only its *shape* — a
syntactically safe query that returns wrong data still passes; that's
`eval/`'s job, not this folder's.
