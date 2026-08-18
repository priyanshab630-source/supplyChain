from PROJECT.factories.agent_factory import build_agent
from PROJECT.middleware.stacks import tank_agent_middleware
from PROJECT.llm.groq import get_groq_model

from PROJECT.tools.consumption_forcast_tools import forecast_tool


def build_forecast_agent():
    model = get_groq_model()

    return build_agent(
        tools=[forecast_tool],
        system_prompt="""
You are a supply chain analyst.

Forecast questions -> forecast_tool
Use forecast_tool whenever the user asks about:

- demand forecast
- future consumption
- next day usage
- next week usage
- stockout prediction
- inventory projection
- forecast inventory


Always summarize the forecast results clearly.

Final output should be shown in tabular format.
""",
        middleware=tank_agent_middleware(model),
        model=model,
    )