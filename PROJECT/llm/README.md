# PROJECT/llm/

## Why this exists
One place that constructs the actual chat model client, so every
agent/orchestrator/middleware that needs an LLM (planner, final
answer, KG Cypher generation, `SummarizationMiddleware`,
`LLMToolSelectorMiddleware`, P8's judge scorer) gets it from the same
function instead of each hardcoding a model name and API key lookup.

## Files & Functions
| File | Function | What it does |
|---|---|---|
| `groq.py` | `get_groq_model()` | Returns a configured Groq chat model client. Called throughout the codebase — `agents/kg_agent.py`, `graph/nodes.py`'s final-answer chain, `graph/planner.py`, `factories/agent_factory.py`, `eval/llm_judge_scoring.py`. |

## Note
This is the one file every other folder in `PROJECT/` implicitly
depends on for LLM access — if Groq's API key is missing/invalid,
expect failures across planner routing, KG questions, final answer
synthesis, and the P8 eval suite's judge scoring, not just one
isolated feature. Check this first if multiple unrelated things break
at once.
