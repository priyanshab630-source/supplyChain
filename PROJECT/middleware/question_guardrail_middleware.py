"""
Custom middleware: enforces the existing input guardrail
(guardrails/input_guardrail.py) as a before_agent hook, so it's
applied to any create_agent-based agent this middleware is attached
to, in addition to (not instead of) the check already wired into
graph_stream.py's stream_graph_events() for the whole pipeline's
entry point.

This is deliberately simple: it raises GuardrailViolation directly
rather than attempting an in-graph short-circuit, since before_agent
hooks return state updates (a dict or None) and the exact mechanism
for aborting the REST of a create_agent run from a node-style hook
isn't something I could confirm against your specific installed
LangChain version. Raising is the safe, unambiguous choice - it
propagates up to whatever try/except already wraps this agent's
invocation (e.g. kg_node's existing try/except in nodes.py), which is
the same pattern every other guardrail in this codebase already relies
on.
"""

from langchain.agents.middleware import before_agent

from PROJECT.guardrails.input_guardrail import validate_question


@before_agent
def question_guardrail_middleware(state, runtime):
    messages = state.get("messages", [])

    if not messages:
        return None

    last_message = messages[-1]
    content = getattr(last_message, "content", None)

    if isinstance(content, str):
        validate_question(content)  # raises GuardrailViolation - let it propagate

    return None