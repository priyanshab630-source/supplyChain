"""
Guardrail: kg_tools.py's generate_cypher() is LLM output, and
execute_cypher()/visualize_subgraph() previously ran that Cypher
directly against Neo4j with NO validation - a genuine injection
surface. Nothing stopped a generated (or, in the LLM-agent path, an
indirectly user-influenced) query from containing DELETE, MERGE,
SET, DROP, or an admin/APOC procedure call.

This is a WHITELIST, not a blacklist: only single-statement,
read-only MATCH...RETURN queries pass. That's a deliberately narrow
bar - your own generate_cypher() prompt already only ever asks for
this shape (see kg_tools.py's system prompt: "ALWAYS return t,r,n",
"Never RETURN path"), so this guardrail doesn't restrict any
legitimate query your system currently produces. It only rejects
queries that shouldn't have been generated in the first place.
"""

import re
from PROJECT.guardrails.exceptions import GuardrailViolation


_FORBIDDEN_KEYWORDS = [
    "CREATE", "MERGE", "DELETE", "DETACH", "SET", "REMOVE", "DROP",
    "CALL", "LOAD CSV", "FOREACH",
]
_FORBIDDEN_PATTERN = re.compile(r"\b(" + "|".join(_FORBIDDEN_KEYWORDS) + r")\b", re.IGNORECASE)

_MULTI_STATEMENT_PATTERN = re.compile(r";\s*\S")


def validate_cypher(cypher: str):
    """
    Raises GuardrailViolation if the query isn't a safe,
    single-statement, read-only MATCH...RETURN query. Returns None
    (silently) if it passes.
    """

    stripped = (cypher or "").strip()

    if not stripped:
        raise GuardrailViolation("cypher_guardrail", "Empty query.")

    if not re.match(r"^\s*MATCH\b", stripped, re.IGNORECASE):
        raise GuardrailViolation(
            "cypher_guardrail",
            "Query must start with MATCH - only read queries are permitted.",
        )

    forbidden = _FORBIDDEN_PATTERN.search(stripped)
    if forbidden:
        raise GuardrailViolation(
            "cypher_guardrail",
            f"Query contains a forbidden write/admin keyword: {forbidden.group(1)}",
        )
    if _MULTI_STATEMENT_PATTERN.search(stripped):
        raise GuardrailViolation(
            "cypher_guardrail",
            "Multiple statements are not permitted in a single query.",
        )
    if "RETURN" not in stripped.upper():
        raise GuardrailViolation(
            "cypher_guardrail",
            "Query has no RETURN clause - refusing to execute a query with no readable output.",
        )