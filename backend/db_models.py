from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column, JSON


class Thread(SQLModel, table=True):
    """One conversation. thread_id is generated client-side per session."""

    id: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    """A single chat turn - either the user's question or the final answer."""

    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: str = Field(foreign_key="thread.id", index=True)
    role: str  
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentRun(SQLModel, table=True):
    """
    One row per node that fires during a graph run (inventory,
    forecast, supplier, kg, network, risk, recommendation,
    final_answer). This is what lets the frontend replay a past
    turn's flow, not just its final answer.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: str = Field(foreign_key="thread.id", index=True)
    agent_name: str
    result: dict = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
