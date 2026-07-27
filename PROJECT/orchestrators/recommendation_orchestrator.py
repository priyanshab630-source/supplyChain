from PROJECT.factories.agent_factory import build_agent

from PROJECT.tools.recommendation_tools import (
    generate_recommendation,
)


def build_recommendation_agent():

    return build_agent(

        tools=[
            generate_recommendation,
        ],

        system_prompt="""
You are a Supply Chain Recommendation Agent.

Responsibilities

Read

• Inventory

• Supplier

• Risk

Generate the best business recommendation.

Always use the generate_recommendation tool.

Do not invent information.

Return only the recommendation.
"""
    )