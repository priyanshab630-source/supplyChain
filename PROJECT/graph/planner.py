from PROJECT.llm.groq import get_groq_model
from PROJECT.graph.prompts import PLANNER_PROMPT

llm = get_groq_model()

VALID_AGENTS = [
    "inventory",
    "forecast",
    "supplier",
    "kg",
    "risk",
    "recommendation",
    "network",
    "malfunction",
    "allocation",
    "shipment_delay",
]


def build_plan(question: str) -> list[str]:
    """
    Uses the Planner LLM to decide which
    agents should execute.

    Returns an ordered execution plan.
    """

    chain = PLANNER_PROMPT | llm

    response = chain.invoke({"question": question})

    raw_plan = response.content

    print("\nPlanner Output")
    print(raw_plan)

    plan = [
        agent.strip().lower()
        for agent in raw_plan.split(",")
        if agent.strip()
    ]

    plan = [agent for agent in plan if agent in VALID_AGENTS]

    unique_plan = []
    seen = set()

    for agent in plan:
        if agent not in seen:
            unique_plan.append(agent)
            seen.add(agent)

    plan = unique_plan

    if "recommendation" in plan and "risk" not in plan:
        idx = plan.index("recommendation")
        plan.insert(idx, "risk")
    if "malfunction" in plan:
        plan = ["malfunction"] + [a for a in plan if a != "malfunction"]

    print("\nValidated Execution Plan")
    print(plan)

    return plan
