import json
import os
import webbrowser

from pyvis.network import Network
from langchain.tools import tool

from PROJECT.llm.groq import get_groq_model
from PROJECT.database.neo4j import graph

model = get_groq_model()

def build_tank_cypher(tank_id: str) -> str:
    """
    Deterministically build the fixed relationship-lookup Cypher
    query for a single tank. No LLM call involved.
    """

    return (
        f"MATCH (t:Tank {{tank_id:'{tank_id}'}})-[r]-(n)\n"
        f"RETURN t,r,n\n"
        f"LIMIT 25"
    )


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


@tool
def execute_cypher(cypher: str):
    """
    Execute Cypher on Neo4j.
    """

    records = graph.query(cypher)

    return records[:25]



@tool
def generate_insights(records):
    """
    Generate business insights from Neo4j query results.
    """

    prompt = f"""
    You are a supply chain analyst.

    Analyze

    {json.dumps(records, indent=2, default=str)}


    Provide concise business insights.
    """

    return model.invoke(prompt).content


@tool
def visualize_subgraph(cypher: str):
    """
    Visualize Neo4j subgraph.
    """

    records = graph.query(cypher)
    print(len(records))
    print(records[:2])

    net = Network(height="750px",width="100%",bgcolor="white",font_color="black")

    added_nodes = set()

    for row in records[:25]:

        source = row.get("t")
        target = row.get("n")
        rels = row.get("r")

        if source is None or target is None:
            continue

        source_id = ( source.get("tank_id") or source.get("name") or source.get("site_name") or str(source))
        target_id = (target.get("tank_id") or target.get("name") or target.get("site_name") or str(target))

        if source_id not in added_nodes:
            net.add_node(source_id, label=source_id)
            added_nodes.add(source_id)

        if target_id not in added_nodes:
            net.add_node(target_id, label=target_id)
            added_nodes.add(target_id)

        if isinstance(rels, list):
            for rel in rels:
                if isinstance(rel, tuple):
                    if len(rel) >= 3:
                        relationship = rel[1]
                    else:
                        relationship = "RELATED"
                else:
                    relationship = str(rel)
                net.add_edge(source_id, target_id, label=relationship)
        elif isinstance(rels, tuple):
            if len(rels) >= 3:
                relationship = rels[1]
            else:
                relationship = "RELATED"

            net.add_edge(source_id,target_id,label=relationship)
        else:
            net.add_edge(source_id,target_id,label=str(rels))

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