"""
P1: seeds BACKS_UP relationships into Neo4j between tanks that share
a switchover_group, so the KG agent can answer failover questions
("if this tank fails, what covers it?") via a real graph traversal
instead of guessing from prose.

Run after add_switchover_and_contract_data.py, and after your
existing Tank/Supplier/Site nodes are already loaded into Neo4j:

    python -m PROJECT.scripts.seed_backs_up_relationships
"""

import pandas as pd
from PROJECT.database.postgres import data_engine
from PROJECT.database.neo4j import get_graph

def run():
    tank_df = pd.read_sql_table("tank_master", data_engine)
    graph = get_graph()
    groups = tank_df.dropna(subset=["switchover_group"]).groupby("switchover_group")
    created = 0
    for group_name, group_df in groups:
        tank_ids = group_df["tank_id"].tolist()
        for i, tank_a in enumerate(tank_ids):
            for tank_b in tank_ids[i + 1:]:
                graph.query(
                    """
                    MATCH (a:Tank {tank_id: $tank_a}), (b:Tank {tank_id: $tank_b})
                    MERGE (a)-[:BACKS_UP]->(b)
                    MERGE (b)-[:BACKS_UP]->(a)
                    """,
                    {"tank_a": tank_a, "tank_b": tank_b},
                )
                created += 2
    print(f"Seeded {created} BACKS_UP relationships across {len(groups)} switchover groups.")

if __name__ == "__main__":
    run()
