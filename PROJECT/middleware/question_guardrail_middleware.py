from langchain.agents.middleware import before_agent
from PROJECT.guardrails.input_guardrail import validate_question


@before_agent
def question_guardrail_middleware(state, runtime):
    messages = state.get("messages", [])

    if not messages:
        return None

    last_message = messages[-1]
    content = getattr(last_message, "content", None)

    if isinstance(content, str):
        validate_question(content) 
    return None