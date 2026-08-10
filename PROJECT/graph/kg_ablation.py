"""
P1 ablation: does grounding the KG agent in BACKS_UP relationships
(seeded by scripts/seed_backs_up_relationships.py) actually improve
its answers on failover/switchover questions, versus the same agent
with no BACKS_UP relationships in the graph at all?

This is a small, honest STARTING harness, not a finished eval suite:

- SCENARIOS below need to be reviewed/extended with real questions
  and real expected tank ids once Intel's actual switchover data is
  in. Right now they're written against the DUMMY pairing produced
  by add_switchover_and_contract_data.py - do not treat the numbers
  this produces as a real result until the scenarios and the
  underlying data are both real.
- Scoring is a simple "did the expected tank id appear in the
  answer" check - good enough for a first number, but swap for
  something like RAGAS's faithfulness/answer-relevancy scoring
  before this goes anywhere near a paper.

RUN ORDER (only the first time, or whenever your CSVs change):
    python -m PROJECT.data_loader.seed_from_csv
    python -m PROJECT.data_loader.add_switchover_and_contract_data

Then just:
    python -m PROJECT.graph.kg_ablation

This script now RE-SEEDS BACKS_UP relationships itself before
Condition A runs and again after Condition B's cleanup - you no
longer need to remember to run seed_backs_up_relationships.py
between runs. (Previously this was a manual step you had to
remember every time; forgetting it silently made Condition A test
the exact same no-grounding state as Condition B, producing a
false "grounding doesn't help" result with no error or warning.)
"""

import re

from PROJECT.agents.kg_agent import KGAgent
from PROJECT.database.neo4j import get_graph
from PROJECT.scripts.seed_backs_up_relationships import run as reseed_backs_up


# Each scenario: a question, and the tank_id(s) a correct answer
# must mention. Fill these in against your actual switchover_group
# assignments before treating results as meaningful.
SCENARIOS = [
    {
        "question": "If Tank 1 malfunctions, which tank backs it up?",
        "expected_tank_ids": ["Tank 2"],
    },
    {
        "question": "What tank covers for Tank 4 if it goes offline?",
        "expected_tank_ids": ["Tank 3"],
    },
    # Add more scenarios here, covering each gas type (Gas A always-on
    # pair, Gas C always-online pool, everything else online/standby)
    # once real switchover_group data exists.
]


def _remove_backs_up_relationships():
    get_graph().query("MATCH ()-[r:BACKS_UP]-() DELETE r")


def _count_backs_up_relationships() -> int:
    result = get_graph().query(
        "MATCH ()-[r:BACKS_UP]->() RETURN count(r) AS count"
    )
    return result[0]["count"] if result else 0


_WHITESPACE_VARIANTS = re.compile(r"[\s\u00a0\u202f\u2007\u2060]+")
_MARKDOWN_EMPHASIS = re.compile(r"[*_`]")


def _normalize(text: str) -> str:
    text = _MARKDOWN_EMPHASIS.sub("", text)
    text = _WHITESPACE_VARIANTS.sub(" ", text)
    return text.strip().lower()


def _score(answer_text: str, expected_tank_ids: list[str]) -> bool:
    normalized_answer = _normalize(answer_text)
    return any(
        _normalize(tank_id) in normalized_answer
        for tank_id in expected_tank_ids
    )


def run_condition(label: str) -> dict:

    agent = KGAgent()
    correct = 0

    for scenario in SCENARIOS:

        result = agent.run(scenario["question"])
        is_correct = _score(result.insights, scenario["expected_tank_ids"])
        correct += int(is_correct)

        print(f"[{label}] Q: {scenario['question']}")
        print(f"[{label}] Correct: {is_correct}")
        print(f"[{label}] Answer: {result.insights[:200]}...\n")

    accuracy = correct / len(SCENARIOS) if SCENARIOS else 0.0

    return {"label": label, "correct": correct, "total": len(SCENARIOS), "accuracy": accuracy}


def run_ablation():

    print("=" * 60)
    print("Ensuring BACKS_UP relationships exist for Condition A...")
    print("=" * 60)
    reseed_backs_up()

    existing = _count_backs_up_relationships()
    print(f"BACKS_UP relationships present: {existing}")

    if existing == 0:
        print(
            "WARNING: 0 BACKS_UP relationships after seeding. Condition A "
            "will NOT actually test grounding - check that tank_master has "
            "a populated switchover_group column (run "
            "add_switchover_and_contract_data.py if not) and that Neo4j "
            "already has your Tank nodes loaded."
        )

    print("=" * 60)
    print("Condition A: WITH BACKS_UP grounding")
    print("=" * 60)
    with_grounding = run_condition("with_grounding")

    print("=" * 60)
    print("Removing BACKS_UP relationships for the control condition...")
    print("=" * 60)
    _remove_backs_up_relationships()

    print("=" * 60)
    print("Condition B: WITHOUT BACKS_UP grounding")
    print("=" * 60)
    without_grounding = run_condition("without_grounding")

    print("=" * 60)
    print("Restoring BACKS_UP relationships (no manual step needed)...")
    print("=" * 60)
    reseed_backs_up()

    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"With grounding:    {with_grounding['correct']}/{with_grounding['total']} ({with_grounding['accuracy']:.1%})")
    print(f"Without grounding: {without_grounding['correct']}/{without_grounding['total']} ({without_grounding['accuracy']:.1%})")

    return with_grounding, without_grounding


if __name__ == "__main__":
    run_ablation()