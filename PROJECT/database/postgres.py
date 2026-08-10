import os

from sqlalchemy import create_engine

# Same DB the backend uses by default - seeding once via
# data_loader/seed_from_csv.py makes the domain data available to
# both the agents AND the backend's chat/run history, as different
# tables in one instance.
DATA_DATABASE_URL = os.getenv(
    "DATA_DATABASE_URL",
    os.getenv("DATABASE_URL", "sqlite:///./supply_chain.db"),
)

data_engine = create_engine(DATA_DATABASE_URL)
