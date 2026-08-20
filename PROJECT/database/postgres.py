import os

from sqlalchemy import create_engine

DATA_DATABASE_URL = os.getenv(
    "DATA_DATABASE_URL",
    os.getenv("DATABASE_URL", "sqlite:///./supply_chain.db"),
)

data_engine = create_engine(DATA_DATABASE_URL)
