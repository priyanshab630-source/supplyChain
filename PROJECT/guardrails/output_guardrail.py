"""
Guardrail on the final synthesized answer, applied inside
final_answer_node right before it's returned/streamed to the user.

Two different failure modes, handled deliberately differently:

- HARD violation (a secret or internal error leaking into the
  answer text) -> replace the answer outright. This should never
  reach a user regardless of how confident the rest of the pipeline
  was.
- SOFT violation (the answer mentions a "Tank N" that doesn't exist
  in tank_master - a grounding/hallucination signal) -> log it, don't
  block. Hard-blocking every unmatched tank mention has a real
  false-positive cost: a user can legitimately ask about a tank that
  doesn't exist, and the CORRECT answer is "no such tank" - which
  necessarily mentions the nonexistent id. Get visibility into how
  often this actually fires on real traffic before deciding whether
  to tighten it into a hard block.
"""

import re

_SECRET_PATTERNS = [
    r"neo4j://[^\s]*:[^\s]*@",   
    r"password\s*[:=]\s*['\"]?\S+",
    r"Traceback \(most recent call last\)",
    r"api[_-]?key\s*[:=]\s*['\"]?\S+",
]
_SECRET_PATTERN = re.compile("|".join(_SECRET_PATTERNS), re.IGNORECASE)

_TANK_ID_PATTERN = re.compile(r"\bTank\s+(\d+)\b")

SAFE_FALLBACK_ANSWER = (
    "I wasn't able to generate a safe answer to this question - "
    "please rephrase it or contact support."
)


def check_for_leakage(answer: str) -> str:
    """
    Hard check. Returns the answer unchanged if safe, or
    SAFE_FALLBACK_ANSWER if a secret/internal-error pattern is
    found. Never raises - a leak should degrade to a generic
    message, not an exception that might itself get logged/surfaced
    somewhere containing the same leaked text.
    """
    if _SECRET_PATTERN.search(answer or ""):
        return SAFE_FALLBACK_ANSWER
    return answer


def find_ungrounded_tank_ids(answer: str, known_tank_ids: set) -> list:
    """
    Soft check. Returns every "Tank N" mentioned in the answer that
    ISN'T in known_tank_ids, sorted for stable logging. Callers
    should log this list (event_log, LangSmith run metadata, etc.),
    not block on it.
    """
    mentioned = {f"Tank {m}" for m in _TANK_ID_PATTERN.findall(answer or "")}
    return sorted(mentioned - known_tank_ids)