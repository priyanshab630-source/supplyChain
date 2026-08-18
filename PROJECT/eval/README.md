# PROJECT/eval/

## Why this exists
P8. The research evaluation suite — turns "does this system actually
work" from a code-review opinion into repeatable, scored test runs.
Two design choices that matter: scenarios are generated FROM your
live data (not hardcoded), and structured-output agents get
deterministic scoring while free-text output gets an LLM judge.

## Files & Functions
| File | Function | What it does |
|---|---|---|
| `scenarios.py` | `generate_malfunction_scenarios()` | One per `switchover_group` with 2+ tanks; acceptable backup is a SET (correct for pooled Gas-C groups, not just pairs). |
| | `generate_allocation_scenarios()` | Two per gas: plain split, and split with the first supplier marked unavailable (tests P3's redistribution path specifically). |
| | `generate_shipment_delay_scenarios()` | For each tank: one delay shorter than its cover (should NOT flag risk), one longer (SHOULD) — tests the actual boundary. |
| | `generate_kg_backup_scenarios()` | One per `BACKS_UP` edge actually in Neo4j — scales automatically as you seed more relationships. |
| `agent_scoring.py` | `score_malfunction()`, `score_allocation()`, `score_shipment_delay()` | Deterministic field checks against typed Pydantic results — no judge variance, fully reproducible. |
| `llm_judge_scoring.py` | `llm_judge_score()` | Groundedness/faithfulness/correctness (0–1 each) for free-text KG answers, via an LLM judge. Fails toward all-zero on error, never toward a silent pass. |
| | `substring_score()` | Cheap secondary check (does the answer mention the right id) — not a substitute for the judge score. |
| `runner.py` | `run_all_evals(repeat, max_scenarios)` | Runs every section N times per scenario (default 3 — surfaces flakiness a single run would hide), resets `tank_status` before/after malfunction scenarios, persists the full summary to `eval_results`. |

## Run
```bash
python -m PROJECT.eval.runner --repeat 5 --max-scenarios 30
```

## ⚠️ Warning
Malfunction and shipment-delay evals write real status changes (with
cleanup, but transiently). **Staging/test database only.**

## What this proves vs. doesn't
**Proves**: the P2/P3/P4 logic behaves correctly relative to whatever
data is currently loaded — including dummy switchover pairing.
**Doesn't prove**: that the dummy data reflects real plant behavior
(blocked on P7), or that judge scores are calibrated to human
judgment — spot-check judge `reasoning` fields by hand before trusting
faithfulness numbers fully.
