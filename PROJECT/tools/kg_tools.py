import json
import os
import webbrowser

from pyvis.network import Network
from langchain.tools import tool

from PROJECT.llm.groq import get_groq_model
from PROJECT.database.neo4j import get_graph

model = get_groq_model()



def build_tank_cypher(tank_id: str) -> str:
    safe_tank_id = tank_id.replace("'", "\\'")
    return (
        f"MATCH (t:Tank {{tank_id:'{safe_tank_id}'}})-[r]-(n) "
        f"RETURN t,r,n LIMIT 25"
    )


def _extract_relationship_type(rels):
    """
    Neo4j results for `r` in `MATCH (t)-[r]-(n) RETURN t,r,n` come
    back as a single list: [start_node_dict, "REL_TYPE", end_node_dict]
    - ONE relationship per row, not a list of multiple relationships.
    Pull just the type string (the only string in that list) out.
    """

    if isinstance(rels, (list, tuple)):
        for item in rels:
            if isinstance(item, str):
                return item
        return "RELATED"

    return str(rels) if rels is not None else "RELATED"



MAX_CONSUMPTION_SAMPLES = 3


def _compact_kg_records(records, max_rows: int = 25):

    if not records:
        return {"tank": None, "relationships": []}

    tank_info = records[0].get("t")

    relationships = []
    consumption_samples = []
    consumption_total = 0

    for row in records[:max_rows]:

        rel_type = _extract_relationship_type(row.get("r"))

        if rel_type == "HAS_CONSUMPTION":
            consumption_total += 1
            if len(consumption_samples) < MAX_CONSUMPTION_SAMPLES:
                consumption_samples.append(row.get("n"))
            continue

        relationships.append({
            "relationship": rel_type,
            "connected_to": row.get("n"),
        })

    if consumption_samples:
        entry = {
            "relationship": "HAS_CONSUMPTION",
            "sample_readings": consumption_samples,
        }
        if consumption_total > len(consumption_samples):
            entry["note"] = (
                f"{consumption_total} hourly consumption readings total; "
                f"showing {len(consumption_samples)} as a sample."
            )
        relationships.append(entry)

    return {
        "tank": tank_info,
        "relationships": relationships,
    }


# Generate Cypher
@tool
def generate_cypher(question: str) -> str:
    """
    Convert natural language into Cypher query.
    """

    prompt = f"""
You are a Neo4j Cypher expert.

        Schema:

        (:Supplier)
        (:Tank)
        (:Site)

        Relationships:

        (:Supplier)-[:STORES]->(:Tank)
        (:Tank)-[:LOCATED_AT]->(:Site)
        (:Supplier)-[:SUPPLIES]->(:Tank)
        ()-[:MAKES]->()
        ()-[:DELIVERS_TO]->()
        ()-[:HAS_CONSUMPTION]->()
        ()-[:BACKS_UP]->()


        Properties:

        Supplier.name
        Tank.tank_id
        Site.site_name

        Take tank_id as :
        Example:
        tank_id = "Tank 15",
        tank_id = "Tank 1",
        tank_id = "Tank 30",


        Take supplier_name as :
        Example:
        "Supplier A"
        "Supplier B"

        Generate Cypher.

        IMPORTANT:
        - Never use Neo4j parameters like $tank_id.
        - Use literal values directly.
        - Return only Cypher.
        - LIMIT 25 for graph visualization
        For graph visualization queries always return:

        VERY IMPORTANT

        For graph visualization ALWAYS generate exactly this pattern.

        MATCH (t:Tank {{tank_id:'Tank 15'}})-[r]-(n)
        RETURN t,r,n
        LIMIT 25

        Rules

        - NEVER use r*
        - NEVER use variable length relationships
        - NEVER use p
        - NEVER RETURN path
        - NEVER RETURN relationships()
        - NEVER RETURN nodes()
        - ALWAYS return t,r,n

        Do not return paths.
        Do not return p.
        Do not return nodes only.



        Question:
        {question}

        Return ONLY Cypher.
"""

    return model.invoke(prompt).content.strip()


# Execute Cypher
@tool
def execute_cypher(cypher: str):
    """
    Execute Cypher on Neo4j.
    """

    records = get_graph().query(cypher)

    return records[:25]



# Generate Insights
@tool
def generate_insights(records, question: str = ""):
    """
    Generate business insights from Neo4j query results.
    """

    compacted = _compact_kg_records(records)

    tank_info = compacted.get("tank")
    tank_label = (
        tank_info.get("tank_id")
        if isinstance(tank_info, dict) and tank_info.get("tank_id")
        else "this tank"
    )

    payload_json = json.dumps(compacted, indent=2, default=str)

    
    MAX_PAYLOAD_CHARS = 6000

    if len(payload_json) > MAX_PAYLOAD_CHARS:
        payload_json = (
            payload_json[:MAX_PAYLOAD_CHARS]
            + "\n... (truncated for length)"
        )

    prompt = f"""
    You are a supply chain analyst.

    User question: {question}

    Analyze the following graph data for {tank_label} and answer the
    user's question directly and concisely, grounded only in this
    data:

    {payload_json}

    Provide concise business insights relevant to the question above.
    """

    return model.invoke(prompt).content


# Visualization
@tool
def visualize_subgraph(cypher: str):
    """
    Visualize Neo4j subgraph.
    """

    records = get_graph().query(cypher)

    print(len(records))
    print(records[:2])

    net = Network(
        height="750px",
        width="100%",
        bgcolor="white",
        font_color="black"
    )

    added_nodes = set()

    for row in records[:25]:

        source = row.get("t")
        target = row.get("n")
        rels = row.get("r")

        if source is None or target is None:
            continue

        source_id = (
            source.get("tank_id")
            or source.get("name")
            or source.get("site_name")
            or str(source)
        )

        target_id = (
            target.get("tank_id")
            or target.get("name")
            or target.get("site_name")
            or str(target)
        )

        if source_id not in added_nodes:
            net.add_node(source_id, label=source_id)
            added_nodes.add(source_id)

        if target_id not in added_nodes:
            net.add_node(target_id, label=target_id)
            added_nodes.add(target_id)

        # `rels` for ONE relationship comes back as
        # [start_node_dict, "REL_TYPE", end_node_dict] - not a list
        # of several relationships. Extract just the type string.
        relationship = _extract_relationship_type(rels)

        net.add_edge(
            source_id,
            target_id,
            label=relationship
        )

    print("Nodes:", len(net.nodes))
    print("Edges:", len(net.edges))

    output = os.path.abspath("graph.html")

    net.save_graph(output)

    webbrowser.open(output)

    return output


@tool
def graph_query(question: str):

    """
    Create graph visualization only when
    graph/network exploration is requested.

    """
    cypher = generate_cypher.invoke(question)

    return visualize_subgraph.invoke(cypher)