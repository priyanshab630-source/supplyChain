from PROJECT.factories.agent_factory import build_agent
from PROJECT.middleware.stacks import tank_agent_middleware
from PROJECT.llm.groq import get_groq_model

from PROJECT.tools.inventory_tools import inventory_risk_tool


def build_inventory_agent():
    model = get_groq_model()

    return build_agent(
        tools=[inventory_risk_tool],
        system_prompt="""
You are an Inventory Expert.

Call inventory_risk_tool EXACTLY ONCE, using the tank ID from the
question. As soon as you receive its result, stop calling tools and
answer the user's question directly using that result. Do not call
inventory_risk_tool a second time under any circumstances - one call
is always sufficient.

Never calculate inventory yourself - only use the tool's numbers.
""",
        middleware=tank_agent_middleware(model),
    )