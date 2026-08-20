"""
P8: LLM-judge scoring for free-text outputs (KG insights, final
pipeline answers) - where a plain substring match either isn't
enough ("does it mention the right tank id" is a different question
from "is this answer actually consistent with the data") or isn't
possible at all (there's no single fixed expected string, only a set
of facts the answer should be faithful to).

Kept deliberately separate from, and secondary to, the deterministic
scoring in agent_scoring.py: judge scores are noisier - this is
another LLM call, another source of variance - and should be read as
a signal, not ground truth, especially from a single run. That's the
whole reason runner.py repeats every scenario multiple times instead
of reporting a single judge score as if it were exact.
"""

import json
import re
from PROJECT.llm.groq import get_groq_model

_JUDGE_PROMPT = """
You are an evaluation judge for a supply-chain question-answering
system. Score the ANSWER against the QUESTION and the list of
EXPECTED FACTS the answer should be consistent with.

QUESTION:
{question}

EXPECTED FACTS (the answer should reflect these, in substance - exact
wording doesn't matter):
{expected_facts}

ANSWER:
{answer}

Score three things, each 0.0 to 1.0:
- groundedness: does the answer avoid inventing facts not supported
  by the expected facts / question context?
- faithfulness: does the answer actually reflect the expected facts,
  without contradicting or omitting the key ones?
- correctness: overall, is this a correct and complete answer to the
  question?

Respond with ONLY a JSON object, no other text, no markdown fences:
{{"groundedness": <float>, "faithfulness": <float>, "correctness": <float>, "reasoning": "<one sentence>"}}
"""

_judge_model = None


def _get_judge_model():
    global _judge_model
    if _judge_model is None:
        _judge_model = get_groq_model()
    return _judge_model


def _strip_json_fences(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def llm_judge_score(question: str, answer: str, expected_facts: list) -> dict:
    """
    Returns {"groundedness": float, "faithfulness": float,
    "correctness": float, "reasoning": str}. On any failure
    (malformed JSON, model/network error), returns all-zero scores
    with the error captured in "reasoning" rather than raising - one
    bad judge call shouldn't abort a whole eval run, but a silent
    default-to-1.0 would be worse: fail toward "looks bad", not
    "looks fine".
    """

    prompt = _JUDGE_PROMPT.format(
        question=question,
        expected_facts="\n".join(f"- {f}" for f in expected_facts) or "(none specified)",
        answer=answer,
    )

    try:
        raw = _get_judge_model().invoke(prompt).content
        parsed = json.loads(_strip_json_fences(raw))

        return {
            "groundedness": float(parsed.get("groundedness", 0.0)),
            "faithfulness": float(parsed.get("faithfulness", 0.0)),
            "correctness": float(parsed.get("correctness", 0.0)),
            "reasoning": str(parsed.get("reasoning", "")),
        }

    except Exception as exc:
        return {
            "groundedness": 0.0,
            "faithfulness": 0.0,
            "correctness": 0.0,
            "reasoning": f"Judge scoring failed: {exc}",
        }


_WHITESPACE_VARIANTS = re.compile(r"[\s\u00a0\u202f\u2007\u2060]+")
_MARKDOWN_EMPHASIS = re.compile(r"[*_`]")


def _normalize(text: str) -> str:
    text = _MARKDOWN_EMPHASIS.sub("", text)
    text = _WHITESPACE_VARIANTS.sub(" ", text)
    return text.strip().lower()


def substring_score(answer_text: str, expected_keywords: list) -> bool:
    """
    Cheap sanity check carried over from the original kg_ablation.py
    - does the answer mention at least one expected keyword/id at
    all. Fast and useful as a pre-check, NOT a substitute for
    llm_judge_score: a correct-looking substring can appear inside an
    otherwise wrong or unfaithful answer.
    """
    normalized_answer = _normalize(answer_text)
    return any(_normalize(k) in normalized_answer for k in expected_keywords)