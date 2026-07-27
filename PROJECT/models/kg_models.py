from pydantic import BaseModel

class KGResult(BaseModel):

    question: str
    cypher_query: str
    records: list[dict]
    insights: str
    graph_path: str | None