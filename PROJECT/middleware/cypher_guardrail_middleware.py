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
            return {"error": str(exc)}

    return handler(request)