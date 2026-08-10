from langchain_neo4j import Neo4jGraph

        
_graph = None


def get_graph() -> Neo4jGraph:
    """
    Lazily connects to Neo4j on first use instead of at import time.
    This means the rest of the app (inventory/forecast/supplier/risk/
    recommendation agents, the FastAPI server, the CLI) starts and
    runs fine even if the Neo4j server isn't up - only questions that
    actually need the KG agent fail, with a clear error surfaced
    through kg_node's existing try/except, instead of the whole
    process crashing on import.
    """
    global _graph

    if _graph is None:
        _graph = Neo4jGraph(
            url="neo4j://127.0.0.1:7687",
            username="neo4j",
            password="Anupri2230"
        )

    return _graph
