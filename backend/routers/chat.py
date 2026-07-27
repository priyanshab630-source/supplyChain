import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from backend.database import get_session
from backend.schemas import AskRequest, NewThreadResponse
from backend.graph_stream import stream_graph_events
from backend import persistence

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/threads", response_model=NewThreadResponse)
def new_thread(session: Session = Depends(get_session)):
    thread_id = str(uuid.uuid4())
    persistence.ensure_thread(session, thread_id)
    return NewThreadResponse(thread_id=thread_id)


@router.post("/ask")
def ask(request: AskRequest, session: Session = Depends(get_session)):
    return StreamingResponse(stream_graph_events(request.question, request.thread_id, session),media_type="text/event-stream",)


@router.get("/threads/{thread_id}/history")
def history(thread_id: str, session: Session = Depends(get_session)):
    messages, runs = persistence.get_thread_history(session, thread_id)
    return {
        "messages": [m.model_dump() for m in messages],
        "runs": [r.model_dump() for r in runs],
    }
