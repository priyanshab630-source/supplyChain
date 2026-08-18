"""
P8: Research evaluation runner.

Ties scenarios.py (what to test, derived from live data) and
agent_scoring.py / llm_judge_scoring.py (how to score it) into one
place that:

1. Runs each scenario REPEAT_COUNT times (default 3), not once. A
   single run tells you almost nothing given how many steps in this
   pipeline are LLM-driven and non-deterministic (planner routing,
   generate_cypher, generate_insights, the final-answer chain, plus
   the judge model itself). Reporting an accuracy number with no
   repeat count and no variance figure was exactly the gap flagged
   as this framework's biggest weakness - this fixes that directly.

2. Resets tank_status before AND after every malfunction scenario
   (and every repeat of the same scenario), so results can't bleed
   between scenarios or between runs of this suite.

3. Writes every run's full results to eval_results (loader.py
   addition) via write_eval_run(), so scores are comparable across
   runs over time - re-run after a code change and diff against the
   last run's summary instead of trusting memory.

WARNING: malfunction evals mutate tank_status and shipment_delay
evals mutate shipment_status (both with cleanup, but transiently).
Run this against a staging/test database, not a production one with
real operators watching a live dashboard.

Run:
    python -m PROJECT.eval.runner
    python -m PROJECT.eval.runner --repeat 5 --max-scenarios 20
"""

import argparse
import statistics
import time
import uuid

from PROJECT.data_loader.loader import load_tank_master_data, write_tank_status, write_eval_run
from PROJECT.agents.malfunction_agent import malfunction_agent
from PROJECT.agents.allocation_agent import allocation_agent
from PROJECT.agents.shipment_delay_agent import shipment_delay_agent
from PROJECT.agents.kg_agent import KGAgent
from PROJECT.eval import scenarios as scenario_gen
from PROJECT.eval.agent_scoring import score_malfunction, score_allocation, score_shipment_delay
from PROJECT.eval.llm_judge_scoring import llm_judge_score, substring_score

DEFAULT_REPEAT_COUNT = 3


def _reset_tanks_to_default(tank_ids):
    """
    Restores a set of tanks to their tank_master default_role at
    1.0x surge with no compensating_for link. Run before AND after
    every malfunction scenario (and every repeat of it) so each run
    starts from a clean, known state instead of whatever the
    previous run left behind.
    """
    tank_df = load_tank_master_data(force_refresh=True)

    for tank_id in tank_ids:
        rows = tank_df.loc[tank_df["tank_id"] == tank_id, "default_role"]
        role = rows.iloc[0] if not rows.empty and rows.iloc[0] else "ONLINE"
        write_tank_status(tank_id, status=role, surge_multiplier=1.0, compensating_for=None)


def run_malfunction_evals(repeat=DEFAULT_REPEAT_COUNT, max_scenarios=20) -> dict:
    scenarios = scenario_gen.generate_malfunction_scenarios(max_scenarios=max_scenarios)
    results = []

    for scenario in scenarios:
        involved = {scenario["tank_id"], *scenario["acceptable_backup_tank_ids"]}
        run_passes = []

        for _ in range(repeat):
            _reset_tanks_to_default(involved)

            try:
                effect = malfunction_agent.report_malfunction(scenario["tank_id"])
                _checks, passed = score_malfunction(effect, scenario["acceptable_backup_tank_ids"])
            except Exception:
                passed = False

            run_passes.append(passed)
            _reset_tanks_to_default(involved)  # cleanup even on failure

        results.append({
            "scenario": {k: (list(v) if isinstance(v, set) else v) for k, v in scenario.items()},
            "pass_rate": sum(run_passes) / len(run_passes),
            "runs": repeat,
        })

    return _summarize("malfunction", results, rate_key="pass_rate")


def run_allocation_evals(repeat=DEFAULT_REPEAT_COUNT, max_scenarios=20) -> dict:
    scenarios = scenario_gen.generate_allocation_scenarios(max_scenarios=max_scenarios)
    results = []

    for scenario in scenarios:
        run_passes = []

        for _ in range(repeat):
            try:
                result = allocation_agent.allocate(
                    gas=scenario["gas"],
                    total_qty_needed=scenario["total_qty_needed"],
                    unavailable_suppliers=scenario.get("unavailable_suppliers", []),
                )
                _checks, passed = score_allocation(result, scenario.get("expected_supplier_count"))
            except Exception:
                passed = False

            run_passes.append(passed)

        results.append({
            "scenario": scenario,
            "pass_rate": sum(run_passes) / len(run_passes),
            "runs": repeat,
        })

    return _summarize("allocation", results, rate_key="pass_rate")


def run_shipment_delay_evals(repeat=DEFAULT_REPEAT_COUNT, max_scenarios=20) -> dict:
    scenarios = scenario_gen.generate_shipment_delay_scenarios(max_pairs=max_scenarios)
    results = []

    for scenario in scenarios:
        run_passes = []

        for _ in range(repeat):
            try:
                result = shipment_delay_agent.report_delay(
                    supplier_name=scenario["supplier_name"],
                    delay_days=scenario["delay_days"],
                    tank_id=scenario["tank_id"],
                )
                _checks, passed = score_shipment_delay(
                    result, scenario["tank_id"], scenario["expect_at_risk"]
                )
            except Exception:
                passed = False

            run_passes.append(passed)

        results.append({
            "scenario": scenario,
            "pass_rate": sum(run_passes) / len(run_passes),
            "runs": repeat,
        })

    return _summarize("shipment_delay", results, rate_key="pass_rate")


def run_kg_evals(repeat=DEFAULT_REPEAT_COUNT, max_scenarios=15) -> dict:
    scenarios = scenario_gen.generate_kg_backup_scenarios(max_scenarios=max_scenarios)
    agent = KGAgent()
    results = []

    for scenario in scenarios:
        substring_passes = []
        faithfulness_values = []
        groundedness_values = []

        for _ in range(repeat):
            try:
                kg_result = agent.run(scenario["question"])
                answer = kg_result.insights
            except Exception as exc:
                answer = f"(agent error: {exc})"

            substring_passes.append(substring_score(answer, scenario["expected_tank_ids"]))

            judge = llm_judge_score(
                question=scenario["question"],
                answer=answer,
                expected_facts=[
                    f"The backup tank is one of: {', '.join(scenario['expected_tank_ids'])}"
                ],
            )
            faithfulness_values.append(judge["faithfulness"])
            groundedness_values.append(judge["groundedness"])

        results.append({
            "scenario": scenario,
            "substring_pass_rate": sum(substring_passes) / len(substring_passes),
            "mean_faithfulness": statistics.mean(faithfulness_values),
            "mean_groundedness": statistics.mean(groundedness_values),
            "faithfulness_stdev": (
                statistics.pstdev(faithfulness_values) if len(faithfulness_values) > 1 else 0.0
            ),
            "runs": repeat,
        })

    return _summarize("kg", results, rate_key="substring_pass_rate")


def _summarize(label, results, rate_key) -> dict:
    if not results:
        return {"label": label, "scenario_count": 0, "overall_pass_rate": None, "results": []}

    pass_rates = [r[rate_key] for r in results]
    overall = statistics.mean(pass_rates)
    variance = statistics.pstdev(pass_rates) if len(pass_rates) > 1 else 0.0

    return {
        "label": label,
        "scenario_count": len(results),
        "overall_pass_rate": overall,
        "pass_rate_stdev_across_scenarios": variance,
        "results": results,
    }


def run_all_evals(repeat=DEFAULT_REPEAT_COUNT, max_scenarios=20) -> dict:
    eval_run_id = str(uuid.uuid4())
    started_at = time.time()

    sections = {
        "kg": run_kg_evals(repeat, max_scenarios),
        "malfunction": run_malfunction_evals(repeat, max_scenarios),
        "allocation": run_allocation_evals(repeat, max_scenarios),
        "shipment_delay": run_shipment_delay_evals(repeat, max_scenarios),
    }

    summary = {
        "eval_run_id": eval_run_id,
        "repeat_count": repeat,
        "duration_seconds": round(time.time() - started_at, 1),
        "sections": sections,
    }

    try:
        write_eval_run(eval_run_id, summary)
    except Exception as exc:
        print(f"[EVAL] Warning: failed to persist eval run: {exc}")

    _print_report(summary)
    return summary


def _print_report(summary):
    print("\n" + "=" * 70)
    print(f"P8 EVAL RUN {summary['eval_run_id']}  (repeat={summary['repeat_count']}, "
          f"{summary['duration_seconds']}s)")
    print("=" * 70)

    for label, section in summary["sections"].items():
        if section["scenario_count"] == 0:
            print(f"\n{label}: no scenarios generated - check the underlying data "
                  "(switchover_group, supplier_contract_shares, BACKS_UP edges, etc.)")
            continue

        print(
            f"\n{label}: {section['scenario_count']} scenario(s), "
            f"overall pass rate {section['overall_pass_rate']:.1%} "
            f"(stdev across scenarios: {section['pass_rate_stdev_across_scenarios']:.1%})"
        )

        if label == "kg":
            mean_f = statistics.mean(r["mean_faithfulness"] for r in section["results"])
            mean_g = statistics.mean(r["mean_groundedness"] for r in section["results"])
            print(f"       mean faithfulness (LLM judge): {mean_f:.2f}, "
                  f"mean groundedness: {mean_g:.2f}")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Run the P8 evaluation suite.")
    parser.add_argument("--repeat", type=int, default=DEFAULT_REPEAT_COUNT)
    parser.add_argument("--max-scenarios", type=int, default=20)
    args = parser.parse_args()

    run_all_evals(repeat=args.repeat, max_scenarios=args.max_scenarios)


if __name__ == "__main__":
    main()