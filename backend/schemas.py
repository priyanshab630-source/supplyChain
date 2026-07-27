from pydantic import BaseModel


class AskRequest(BaseModel):
    thread_id: str
    question: str


class NewThreadResponse(BaseModel):
    thread_id: str