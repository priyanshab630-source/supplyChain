from sqlmodel import Session, select

from backend.db_models import Thread, Message, AgentRun


def ensure_thread(session: Session, thread_id: str) -> Thread:
    thread = session.get(Thread, thread_id)

    if thread is None:
        thread = Thread(id=thread_id)
        session.add(thread)
        session.commit()

    return thread


def save_message(session: Session, thread_id: str, role: str, content: str):
    ensure_thread(session, thread_id)
    message = Message(thread_id=thread_id, role=role, content=content)
    session.add(message)
    session.commit()


def save_agent_run(session: Session, thread_id: str, agent_name: str, result: dict):
    ensure_thread(session, thread_id)
    run = AgentRun(thread_id=thread_id, agent_name=agent_name, result=result)
    session.add(run)
    session.commit()


def get_thread_history(session: Session, thread_id: str):
    messages = session.exec(select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at)).all()
    runs = session.exec(select(AgentRun).where(AgentRun.thread_id == thread_id).order_by(AgentRun.created_at)).all()

    return messages, runs
