from langchain.tools import tool

from PROJECT.agents.risk_manager_agent import RiskAgent

risk_agent = RiskAgent()


@tool
def risk_analysis(
    inventory,
    forecast,
    supplier,
    kg,
):
    """
    Calculate overall supply chain risk.
    """

    return risk_agent.run(
        inventory,
        forecast,
        supplier,
        kg,
    )