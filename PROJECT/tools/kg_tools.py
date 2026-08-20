import json
import os
import re
import webbrowser
from pyvis.network import Network
from langchain.tools import tool
from PROJECT.llm.groq import get_groq_model
from PROJECT.database.neo4j import get_graph
from PROJECT.guardrails.cypher_guardrail import validate_cypher

model = get_groq_model()


def build_tank_cypher(tank_id: str) -> str:
    """
    Deterministic fixed relationship-lookup Cypher for one tank.
    Plain function, NOT an LLM tool - only called directly by the
    KG agent's deterministic fast path (agents/kg_agent.py) and by
    graph_query below when a tank is named in a visualization
    request.
    """

    return (
        f"MATCH (t:Tank {{tank_id:'{tank_id}'}})-[r]-(n)\n"
        f"RETURN t,r,n\n"
        f"LIMIT 25"
    )


def _extract_tank_id(question: str):

    match = re.search(r"tank\s*(\d+)", question, re.IGNORECASE)

    if match:
        return f"Tank {match.group(1)}"

    return None


def _generate_cypher_text(question: str, force_visualization: bool = False) -> str:
    """
    Shared prompt builder for generate_cypher (tool) and graph_query
    (tool, for the case where no tank_id can be extracted and
    build_tank_cypher's fixed template doesn't apply - e.g. "show me
    the graph for Supplier A").

    force_visualization=True makes the t,r,n requirement an
    UNCONDITIONAL instruction instead of something the model has to
    infer from the question's phrasing. Leaving that to inference is
    what caused blank graphs: the model would sometimes alias
    variables differently for a visualization request that didn't
    obviously read as "this needs a graph", and visualize_subgraph
    only recognizes rows with literal t/n keys.
    """

    visualization_instruction = (
        "This is a GRAPH VISUALIZATION query. You MUST return exactly "
        "t, r, n using one of the patterns below - no other field "
        "names, no aggregations, no DISTINCT projections, no renamed "
        "variables."
        if force_visualization else
        "Decide based on the question whether this is a visualization "
        "request (return t,r,n) or a factual question (return whatever "
        "specific fields answer it)."
    )

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
(:Tank)-[:BACKS_UP]->(:Tank)
()-[:MAKES]->()
()-[:DELIVERS_TO]->()
()-[:HAS_CONSUMPTION]->()

Properties:

Supplier.name
Tank.tank_id
Site.site_name

BACKS_UP connects two tanks that cover for each other on a
malfunction/switchover (e.g. "what covers Tank 4 if it fails",
"what's the backup for Tank 4", "which tank should we use if Tank 1
is emptied").

Take tank_id as:
Example: "Tank 15", "Tank 1", "Tank 30"

Take supplier_name as:
Example: "Supplier A", "Supplier B"

{visualization_instruction}

IMPORTANT:
- Never use Neo4j parameters like $tank_id.
- Use literal values directly.
- Return only Cypher.
- If the natural first attempt is an exact match (=) on a name or
  tank_id, prefer toLower(x) CONTAINS toLower('...') instead when
  robustness matters more than precision.
- LIMIT 25 for graph visualization.

For graph visualization queries, generate exactly one of these
patterns (substituting the real anchor node/property):

Anchored on a tank:

MATCH (t:Tank {{tank_id:'Tank 15'}})-[r]-(n)
RETURN t,r,n
LIMIT 25

Anchored on a supplier:

MATCH (t:Supplier {{name:'Supplier A'}})-[r]-(n)
RETURN t,r,n
LIMIT 25

Rules:
- NEVER use r*
- NEVER use variable length relationships
- NEVER use p
- NEVER RETURN path
- NEVER RETURN relationships()
- NEVER RETURN nodes()
- For visualization queries: ALWAYS alias the anchor node as t, the
  relationships as r, and the other nodes as n - exactly these three
  names, nothing else, no exceptions.
- For non-visualization factual questions: return whatever specific
  fields answer the question instead of always t,r,n.

Do not return paths. Do not return p. Do not return nodes only.

Question:
{question}

Return ONLY Cypher.
"""

    return model.invoke(prompt).content.strip()


@tool
def generate_cypher(question: str) -> str:
    """
    Convert a natural language question into Cypher.
    """

    return _generate_cypher_text(question, force_visualization=False)



@tool
def execute_cypher(cypher: str):
    """
    Execute Cypher on Neo4j.
    """
 
    validate_cypher(cypher)  # raises GuardrailViolation before anything touches Neo4j
 
    records = get_graph().query(cypher)
 
    return records[:25]


@tool
def generate_insights(records):
    """
    Generate a plain-language business answer from Neo4j query
    results. Use this for factual/tabular questions - NOT for
    visualization requests.
    """

    prompt = f"""
You are a supply chain analyst.

Analyze the following Neo4j query results and answer the user's
underlying question directly and concisely.

Format your answer the way a knowledgeable assistant would in a
chat interface: bold the label for every specific figure or fact
(e.g. **Supplier:** Supplier B), use a bullet list for more than
two distinct facts, and use a short markdown table instead of
bullets when presenting the same fields across multiple records
(e.g. several tanks or suppliers). Never show raw JSON or an
unlabeled dump of fields to the user.

{json.dumps(records, indent=2, default=str)}
"""

    return model.invoke(prompt).content


@tool
def visualize_subgraph(cypher: str):
    """
    Render a Neo4j subgraph to an HTML file and open it. Only call
    this for explicit visualization requests - use generate_insights
    for factual/tabular answers instead.
    """

    validate_cypher(cypher)
    graph = get_graph()
    records = graph.query(cypher)
    net = Network(height="750px", width="100%", bgcolor="white", font_color="black")
    added_nodes = set()

    for row in records[:25]:
        source = row.get("t")
        target = row.get("n")
        rels = row.get("r")

        if source is None or target is None:
            continue

        source_id = (source.get("tank_id") or source.get("name") or source.get("site_name") or str(source))
        target_id = (target.get("tank_id") or target.get("name") or target.get("site_name") or str(target))

        if source_id not in added_nodes:
            net.add_node(source_id, label=source_id)
            added_nodes.add(source_id)

        if target_id not in added_nodes:
            net.add_node(target_id, label=target_id)
            added_nodes.add(target_id)

        if isinstance(rels, list):
            for rel in rels:
                relationship = rel[1] if isinstance(rel, tuple) and len(rel) >= 3 else "RELATED"
                net.add_edge(source_id, target_id, label=relationship)
        elif isinstance(rels, tuple):
            relationship = rels[1] if len(rels) >= 3 else "RELATED"
            net.add_edge(source_id, target_id, label=relationship)
        else:
            net.add_edge(source_id, target_id, label=str(rels))

    if not added_nodes:
        print(f"WARNING: visualize_subgraph produced an EMPTY graph for cypher:\n{cypher}")
        print(f"Raw records returned (first 3): {records[:3]}")

    output = os.path.abspath("graph.html")
    net.save_graph(output)
    webbrowser.open(output)

    return output


@tool
def graph_query(question: str):
    """
    Generate Cypher AND render the resulting subgraph in one step.
    Only call this for explicit visualization/graph-display
    requests - for anything else, use generate_cypher + execute_cypher
    + generate_insights instead.
    """

    tank_id = _extract_tank_id(question)
    if tank_id:
        cypher = build_tank_cypher(tank_id)
    else:
        cypher = _generate_cypher_text(question, force_visualization=True)

    return visualize_subgraph.invoke(cypher)
