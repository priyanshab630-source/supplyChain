

"""
Persistent LangGraph checkpointing - replaces InMemorySaver(), which
loses every in-flight conversation the instant the process restarts
(state lives only in a Python dict in memory, nowhere on disk). This
module picks a persistent backend automatically from DATABASE_URL,
mirroring the same sqlite-vs-postgres branching backend/database.py
already does for the app's own tables:

- sqlite:// -> SqliteSaver (file-based, survives restarts, zero
  extra infrastructure - good for local/dev, matches your existing
  sqlite fallback default)
- postgresql:// -> PostgresSaver backed by a connection pool (for a
  real deployment with Postgres already running)

Scope note: this fixes "state survives a process restart," which is
what InMemorySaver couldn't do. It is NOT cross-session long-term
memory (recalling facts from a DIFFERENT thread_id) - that would be
a separate, bigger feature. This is specifically the persistence fix.

New dependencies:
    pip install langgraph-checkpoint-sqlite       # if DATABASE_URL is sqlite
    pip install langgraph-checkpoint-postgres psycopg[binary] psycopg-pool   # if postgresql
"""

import os
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./supply_chain.db")

# LangGraph's Postgres checkpointer uses psycopg directly and wants a
# plain postgresql://... URI - NOT SQLAlchemy's postgresql+psycopg2://
# style suffix. If your DATABASE_URL already uses a SQLAlchemy driver
# suffix, set LANGGRAPH_DB_URL separately rather than relying on
# string surgery to convert it (safer than guessing at URL parsing).
CHECKPOINT_DB_URL = os.getenv("LANGGRAPH_DB_URL", DATABASE_URL)

_checkpointer_instance = None


def get_checkpointer():
    """
    Returns a singleton persistent checkpointer. Call once at import
    time in workflow.py - same usage as InMemorySaver() was, just
    swapped:

        checkpointer = get_checkpointer()   # was: InMemorySaver()
        graph = builder.compile(checkpointer=checkpointer)
    """
    global _checkpointer_instance

    if _checkpointer_instance is not None:
        return _checkpointer_instance

    if CHECKPOINT_DB_URL.startswith("sqlite"):
        

        db_path = CHECKPOINT_DB_URL.replace("sqlite:///", "")
        # check_same_thread=False for the same reason
        # backend/database.py already sets it on the SQLAlchemy side -
        # FastAPI can hit this from more than one thread.
        conn = sqlite3.connect(db_path, check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        checkpointer.setup()  # creates the checkpoint tables if they don't exist yet - safe every startup

    elif CHECKPOINT_DB_URL.startswith("postgresql://"):
        

        pool = ConnectionPool(
            conninfo=CHECKPOINT_DB_URL,
            max_size=20,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()

    else:
        raise ValueError(
            f"Unsupported DATABASE_URL/LANGGRAPH_DB_URL scheme for checkpointing: "
            f"'{CHECKPOINT_DB_URL}' - expected sqlite:// or postgresql://"
        )

    _checkpointer_instance = checkpointer
    return checkpointer