"""
Custom middleware: applies the existing Cypher guardrail
(guardrails/cypher_guardrail.py) as a wrap_tool_call hook, so it's
enforced automatically on ANY tool call whose args contain a `cypher`
field - not just the two call sites (execute_cypher, visualize_subgraph)
that were patched by hand earlier in kg_tools_patch.py.

This doesn't replace that earlier patch - keep both. Defense in depth:
the function-level check in kg_tools.py protects even code paths that
don't go through create_agent/middleware at all (e.g. kg_agent.py's
deterministic _run_deterministic path, which calls
execute_cypher.invoke() directly). This middleware additionally
protects the create_agent-based KG agent's tool-calling LOOP itself,
catching it one layer earlier, before the tool function body even runs.

NOTE ON VERIFICATION: request.tool_call's exact shape (dict keys,
whether it's `request.tool_call["name"]`/`["args"]` or attribute
access) is based on current LangChain middleware docs/examples, not
your installed version specifically - print(request.tool_call) once
during testing to confirm the shape matches before trusting this in
production, since agent middleware is a newer LangChain API and field
names have moved before (see the LLMToolSelectorMiddleware GitHub
issue referenced in the architecture note - this whole subsystem is
young enough to double-check against your installed version).
"""

from langchain.agents.middleware import wrap_tool_call

from PROJECT.guardrails.cypher_guardrail import validate_cypher
from PROJECT.guardrails.exceptions import GuardrailViolation


@wrap_tool_call
def cypher_guardrail_middleware(request, handler):
    tool_args = request.tool_call.get("args", {}) or {}
    cypher = tool_args.get("cypher")

    if cypher is not None:
        try:
            validate_cypher(cypher)
        except GuardrailViolation as exc:
            # Short-circuit: return an error payload instead of
            # calling handler(request), so the tool never executes.
            # Matches the {"error": ...} shape your own tools already
            # return on failure, so the calling agent's error-handling
            # doesn't need to special-case this.
            return {"error": str(exc)}

    return handler(request)