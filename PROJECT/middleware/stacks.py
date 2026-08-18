"""
Composes PROJECT.factories.agent_factory.default_middleware() (your
production-hardening stack: summarization, tool retry, tool/model call
limits) together with this project's custom middleware (guardrails,
tank_id normalization, audit logging), so each orchestrator doesn't
hand-assemble its own list and risk forgetting a piece.

Every stack starts with question_guardrail_middleware - reject bad
input before summarizing or rate-limiting it, that's wasted work on a
question that's about to be rejected anyway - and ends with
tool_call_audit_middleware, closest to the real tool call.

Note: build_agent()/AgentOrchestrator calls get_groq_model() itself
internally for the actual model= passed to create_agent(). The `model`
you pass into these stack builders is used ONLY for
SummarizationMiddleware's own model= (it can legitimately be a
different/cheaper model than the main agent model). If you want the
exact same model INSTANCE reused everywhere instead of two separate
ChatGroq clients, that requires a small change to AgentOrchestrator to
accept a pre-built model - worth doing later, not blocking anything
today.
"""

from PROJECT.factories.agent_factory import default_middleware
from PROJECT.middleware.question_guardrail_middleware import question_guardrail_middleware
from PROJECT.middleware.tank_id_normalizer_middleware import tank_id_normalizer_middleware
from PROJECT.middleware.cypher_guardrail_middleware import cypher_guardrail_middleware
from PROJECT.middleware.tool_call_audit_middleware import tool_call_audit_middleware


def tank_agent_middleware(model=None):
    """For InventoryAgent/ForecastAgent orchestrators - single tank_id arg, no Cypher."""
    return (
        [question_guardrail_middleware]
        + default_middleware(model)
        + [tank_id_normalizer_middleware, tool_call_audit_middleware]
    )


def supplier_agent_middleware(model=None):
    """For SupplierAgent's orchestrator - no tank_id-shaped arg, no Cypher."""
    return (
        [question_guardrail_middleware]
        + default_middleware(model)
        + [tool_call_audit_middleware]
    )


def kg_agent_middleware(model=None, selector_model=None, max_tools=3):
    """
    For the KG orchestrator specifically - the one with 4 tools worth
    narrowing via LLMToolSelectorMiddleware, and the one that actually
    touches Cypher/Neo4j, hence cypher_guardrail_middleware.
    """
    from langchain.agents.middleware import LLMToolSelectorMiddleware

    return (
        [question_guardrail_middleware]
        + default_middleware(model)
        + [
            LLMToolSelectorMiddleware(
                model=selector_model,  # None -> falls back to the agent's main model
                max_tools=max_tools,
                always_include=["generate_cypher", "execute_cypher"],
            ),
            cypher_guardrail_middleware,
            tool_call_audit_middleware,
        ]
    )