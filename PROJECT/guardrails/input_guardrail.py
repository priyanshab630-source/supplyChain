"""
Guardrail: a first line of defense on the raw user question, applied
before it's persisted, sent to any LLM, or used to route the graph.

This is NOT a substitute for the Cypher guardrail - that one still
runs regardless of what gets past this one, since a question passing
this check says nothing about what the KG agent later generates. This
is a cheap, fast, honest-about-its-limits check: it catches the
obvious cases (empty input, absurd length, a handful of common
prompt-injection phrasings), not a jailbreak classifier. A determined
attacker can phrase around any fixed pattern list - treat this as
raising the bar, not a guarantee.
"""

import re

from PROJECT.guardrails.exceptions import GuardrailViolation

MAX_QUESTION_LENGTH = 2000

_INJECTION_PATTERNS = [
    r"ignore (all|the|your) (previous|prior|above) instructions",
    r"disregard (all|the|your) (previous|prior|above) instructions",
    r"you are now",
    r"system prompt",
    r"reveal your (instructions|prompt|system prompt)",
    r"act as (if|though) you (are|were)",
]
_INJECTION_PATTERN = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def validate_question(question: str):
    """
    Raises GuardrailViolation on: empty input, excessive length (a
    cheap cost/abuse guard), or a known prompt-injection phrasing.
    Returns None if it passes.
    """

    if not question or not question.strip():
        raise GuardrailViolation("input_guardrail", "Question is empty.")

    if len(question) > MAX_QUESTION_LENGTH:
        raise GuardrailViolation(
            "input_guardrail",
            f"Question exceeds {MAX_QUESTION_LENGTH} characters.",
        )
    if _INJECTION_PATTERN.search(question):
        raise GuardrailViolation(
            "input_guardrail",
            "Question matches a known prompt-injection pattern.",
        )