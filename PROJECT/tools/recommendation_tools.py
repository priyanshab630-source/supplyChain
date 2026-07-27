from langchain.tools import tool

from PROJECT.agents.recommendation_agent import RecommendationAgent

recommendation_agent = RecommendationAgent()


@tool
def generate_recommendation(
    inventory,
    supplier,
    risk,
):
    """
    Generate business recommendation.
    """

    return recommendation_agent.run(
        inventory,
        supplier,
        risk,
    )