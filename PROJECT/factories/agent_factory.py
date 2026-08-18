from langchain.agents import create_agent
from langchain.agents.middleware import (
    SummarizationMiddleware,
    ToolRetryMiddleware,
    ToolCallLimitMiddleware,
    ModelCallLimitMiddleware,
)
from langchain_core.messages import HumanMessage
from PROJECT.llm.groq import get_groq_model


def default_middleware(model=None):
    model = model or get_groq_model()
    return [
        SummarizationMiddleware( model=model,
            trigger=("messages", 20),
            keep=("messages", 10),
        ),

        ToolRetryMiddleware(
            max_retries=2,
        ),

        ToolCallLimitMiddleware(
            run_limit=8,
            exit_behavior="continue",
        ),

        ModelCallLimitMiddleware(
            run_limit=8,
            exit_behavior="end",
        ),
    ]


class AgentOrchestrator:

    def __init__(self, system_prompt, tools, middleware=None, model=None):
        model = model or get_groq_model()
        self.agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            middleware=(
                middleware
                if middleware is not None
                else default_middleware(model)
            ),
        )
    def run(self, question: str):
        response = self.agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content=question
                    )
                ]
            }
        )
        return {"messages": response["messages"]}


def build_agent(system_prompt, tools, middleware=None, model=None):
    return AgentOrchestrator(
        system_prompt,
        tools,
        middleware=middleware,
        model=model,
    )