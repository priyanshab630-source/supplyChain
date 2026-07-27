# import os

# from sqlmodel import create_engine, Session, SQLModel

# # postgresql://user:password@host:5432/dbname
# DATABASE_URL = os.getenv(
#     "DATABASE_URL",
#     "postgresql://postgres:password@localhost:5432/supply_chain",
# )

# engine = create_engine(DATABASE_URL, echo=False)


# def init_db():
#     """Create tables if they don't exist yet. Call once on startup."""
#     SQLModel.metadata.create_all(engine)


# def get_session():
#     """FastAPI dependency - one DB session per request."""
#     with Session(engine) as session:
#         yield session

import os
from sqlmodel import create_engine, Session, SQLModel

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./supply_chain.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session