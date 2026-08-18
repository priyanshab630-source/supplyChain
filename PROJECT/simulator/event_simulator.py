"""
P5: Dynamic Event Simulation.

The point of this module is exactly what the requirement says: stop
requiring someone to type a question every time something happens.
Each `simulate_*` function mutates state the SAME WAY a real
detector eventually would (writing to tank_status / shipment_status
via the exact functions P2/P4 already expose), then automatically
runs the full LangGraph pipeline for a natural follow-up question -
so you see the surge/risk/recommendation chain react on its own,
end to end, in one call.

Nothing here duplicates P2/P3/P4 logic. This module only:
  1. Calls malfunction_agent.report_malfunction() / recovery writes
  2. Calls shipment_delay_agent.report_delay() / clear_shipment_delay()
  3. Logs the event to event_log for an audit trail
  4. Runs run_graph() on a follow-up question and returns the answer

Usage (from repo root):

    python -m PROJECT.simulator.event_simulator tank-malfunction "Tank 1"
    python -m PROJECT.simulator.event_simulator tank-recovery "Tank 1" --backup "Tank 2"
    python -m PROJECT.simulator.event_simulator shipment-delay "Supplier A" 3
    python -m PROJECT.simulator.event_simulator shipment-delay "Supplier A" 5 --tank "Tank 12"
    python -m PROJECT.simulator.event_simulator shipment-recovery "Supplier A" "Tank 12"
    python -m PROJECT.simulator.event_simulator supplier-outage "Supplier B"
    python -m PROJECT.simulator.event_simulator history

Or import directly:

    from PROJECT.simulator.event_simulator import simulate_tank_malfunction
    result = simulate_tank_malfunction("Tank 1")
    print(result["pipeline_answer"])
"""

import argparse
import uuid

from PROJECT.data_loader.loader import (
    load_tank_master_data,
    write_tank_status,
    clear_shipment_delay,
    write_event_log,
    load_event_log,
    get_backup_for,
)
from PROJECT.agents.malfunction_agent import malfunction_agent
from PROJECT.agents.shipment_delay_agent import shipment_delay_agent
from PROJECT.graph.run_graph import run_graph


def _run_pipeline(question: str) -> str:
    """
    Runs the SAME graph every real user question goes through, with a
    fresh thread_id so simulated turns don't pollute a real
    conversation's history.
    """
    thread_id = f"sim-{uuid.uuid4()}"
    result = run_graph(question, thread_id=thread_id, source="simulator")
    return result.get("final_answer", "(no final answer produced)")


def _log_event(event_type: str, details: dict):
    """Logging failures should never abort a simulation - just warn and continue."""
    try:
        write_event_log(event_type, details)
    except Exception as exc:
        print(f"[SIMULATOR] Warning: failed to write event log: {exc}")


def _to_loggable(obj):
    return obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj


# ---------------------------------------------------------------
# Tank malfunction / recovery
# ---------------------------------------------------------------

def simulate_tank_malfunction(tank_id: str) -> dict:
    print(f"\n[SIMULATOR] Injecting malfunction: {tank_id}")

    effect = malfunction_agent.report_malfunction(tank_id)
    _log_event("tank_malfunction", {"tank_id": tank_id, "effect": _to_loggable(effect)})
    print(f"[SIMULATOR] {effect.reasoning}")

    # Ask about whichever tank is now actually carrying the load -
    # this is what proves the surge propagated through inventory ->
    # risk -> recommendation automatically (P6), not just that
    # report_malfunction() itself ran.
    target_tank = effect.backup_tank_id or tank_id
    follow_up = f"What is the current risk and recommendation for {target_tank}?"
    answer = _run_pipeline(follow_up)

    return {"event": "tank_malfunction", "tank_id": tank_id, "effect": effect, "pipeline_answer": answer}


def simulate_tank_recovery(tank_id: str, backup_tank_id: str = None) -> dict:
    """
    Reverses a malfunction: restores tank_id to its tank_master
    default_role at 1.0x, and restores whichever tank was
    compensating for it too. backup_tank_id no longer needs to be
    passed - it's auto-resolved via tank_status.compensating_for
    (set by malfunction_agent when it activated the backup). Pass it
    explicitly only to override that lookup.
    """

    if backup_tank_id is None:
        backup_tank_id = get_backup_for(tank_id)
        if backup_tank_id:
            print(f"[SIMULATOR] Auto-resolved backup tank from tank_status: {backup_tank_id}")

    print(f"\n[SIMULATOR] Recovering {tank_id}" + (f" (releasing {backup_tank_id})" if backup_tank_id else ""))

    tank_master_df = load_tank_master_data(force_refresh=True)

    def _default_role(tid: str, fallback: str) -> str:
        rows = tank_master_df.loc[tank_master_df["tank_id"] == tid, "default_role"]
        return rows.iloc[0] if not rows.empty and rows.iloc[0] else fallback

    write_tank_status(
        tank_id, status=_default_role(tank_id, "ONLINE"), surge_multiplier=1.0, compensating_for=None
    )
    _log_event("tank_recovery", {"tank_id": tank_id})

    if backup_tank_id:
        write_tank_status(
            backup_tank_id,
            status=_default_role(backup_tank_id, "STANDBY"),
            surge_multiplier=1.0,
            compensating_for=None,  # explicit clear - the malfunction that set this is over
        )
        _log_event("tank_recovery", {"tank_id": backup_tank_id, "restored_from": tank_id})

    follow_up = f"What is the current status of {tank_id}?"
    answer = _run_pipeline(follow_up)

    return {
        "event": "tank_recovery",
        "tank_id": tank_id,
        "backup_tank_id": backup_tank_id,
        "pipeline_answer": answer,
    }


# ---------------------------------------------------------------
# Shipment delay / recovery / supplier outage
# ---------------------------------------------------------------

def simulate_shipment_delay(supplier_name: str, delay_days: int, tank_id: str = None) -> dict:
    print(f"\n[SIMULATOR] Delaying {supplier_name}'s shipment by {delay_days} day(s)"
          + (f" for {tank_id}" if tank_id else " (all tanks served)"))

    effect = shipment_delay_agent.report_delay(
        supplier_name=supplier_name, delay_days=delay_days, tank_id=tank_id
    )
    _log_event(
        "shipment_delay",
        {"supplier_name": supplier_name, "delay_days": delay_days, "tank_id": tank_id, "effect": _to_loggable(effect)},
    )
    print(f"[SIMULATOR] {effect.reasoning}")

    if effect.tanks_at_risk:
        target = effect.tanks_at_risk[0]
        follow_up = f"What is the current risk and recommendation for {target}?"
    else:
        follow_up = f"What is the current status of tanks supplied by {supplier_name}?"

    answer = _run_pipeline(follow_up)

    return {
        "event": "shipment_delay",
        "supplier_name": supplier_name,
        "delay_days": delay_days,
        "tank_id": tank_id,
        "effect": effect,
        "pipeline_answer": answer,
    }


def simulate_shipment_recovery(supplier_name: str, tank_id: str) -> dict:
    print(f"\n[SIMULATOR] Clearing delay: {supplier_name} / {tank_id}")

    clear_shipment_delay(supplier_name, tank_id)
    _log_event("shipment_recovery", {"supplier_name": supplier_name, "tank_id": tank_id})

    follow_up = f"What is the current status of {tank_id}?"
    answer = _run_pipeline(follow_up)

    return {
        "event": "shipment_recovery",
        "supplier_name": supplier_name,
        "tank_id": tank_id,
        "pipeline_answer": answer,
    }


def simulate_supplier_outage(supplier_name: str) -> dict:
    """
    Calls shipment_delay_agent.report_outage() - its own code path
    with a real 14-day reorder target, not report_delay() fed an
    arbitrary huge number. (See shipment_delay_agent.py's module
    docstring for why that distinction matters: sharing the
    allocation-building logic between delay/outage is fine, but
    sharing the DELAY-LENGTH NUMBER produced a three-year order.)
    """
    print(f"\n[SIMULATOR] Simulating total outage: {supplier_name}")

    effect = shipment_delay_agent.report_outage(supplier_name)
    _log_event("supplier_outage", {"supplier_name": supplier_name, "effect": _to_loggable(effect)})
    print(f"[SIMULATOR] {effect.reasoning}")

    if effect.tanks_at_risk:
        target = effect.tanks_at_risk[0]
        follow_up = f"What is the current risk and recommendation for {target}?"
    else:
        follow_up = f"What is the current status of tanks supplied by {supplier_name}?"

    answer = _run_pipeline(follow_up)

    return {
        "event": "supplier_outage",
        "supplier_name": supplier_name,
        "effect": effect,
        "pipeline_answer": answer,
    }


# ---------------------------------------------------------------
# History
# ---------------------------------------------------------------

def print_history(limit: int = 20):
    df = load_event_log(force_refresh=True)

    if df.empty:
        print("No events logged yet.")
        return

    df = df.sort_values("created_at", ascending=False).head(limit)

    for _, row in df.iterrows():
        print(f"[{row['created_at']}] {row['event_type']}: {row['details']}")


# ---------------------------------------------------------------
# CLI
# ---------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Simulate supply-chain events end-to-end.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p1 = subparsers.add_parser("tank-malfunction")
    p1.add_argument("tank_id")

    p2 = subparsers.add_parser("tank-recovery")
    p2.add_argument("tank_id")
    p2.add_argument("--backup", dest="backup_tank_id", default=None)

    p3 = subparsers.add_parser("shipment-delay")
    p3.add_argument("supplier_name")
    p3.add_argument("delay_days", type=int)
    p3.add_argument("--tank", dest="tank_id", default=None)

    p4 = subparsers.add_parser("shipment-recovery")
    p4.add_argument("supplier_name")
    p4.add_argument("tank_id")

    p5 = subparsers.add_parser("supplier-outage")
    p5.add_argument("supplier_name")

    subparsers.add_parser("history")

    args = parser.parse_args()

    if args.command == "tank-malfunction":
        out = simulate_tank_malfunction(args.tank_id)
    elif args.command == "tank-recovery":
        out = simulate_tank_recovery(args.tank_id, args.backup_tank_id)
    elif args.command == "shipment-delay":
        out = simulate_shipment_delay(args.supplier_name, args.delay_days, args.tank_id)
    elif args.command == "shipment-recovery":
        out = simulate_shipment_recovery(args.supplier_name, args.tank_id)
    elif args.command == "supplier-outage":
        out = simulate_supplier_outage(args.supplier_name)
    elif args.command == "history":
        print_history()
        return

    print("\n" + "=" * 60)
    print("PIPELINE ANSWER")
    print("=" * 60)
    print(out["pipeline_answer"])


if __name__ == "__main__":
    main()