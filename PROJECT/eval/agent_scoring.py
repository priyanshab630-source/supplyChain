"""
P8: deterministic scoring for the structured-output agents (P2/P3/P4).

No LLM judge needed here - report_malfunction/allocate/report_delay
all return typed Pydantic results, so correctness is a direct field
comparison, not a text-faithfulness question. This is the more
reliable half of the eval suite: zero judge variance, fully
reproducible, and it's the part of P8 that specifically closes the
"P2/P3/P4 have never been scored against a labeled expected output"
gap - not just the KG side.
"""


def score_malfunction(effect, acceptable_backup_tank_ids: set) -> tuple:
    """
    Returns (checks_dict, passed_bool). Checks the three things that
    actually matter for correctness: a backup was found at all, it's
    one of the acceptable tanks for this switchover group (not just
    "some tank"), and a surge was actually applied - a backup that
    got "activated" with no consumption increase wouldn't be doing
    anything.
    """

    checks = {
        "backup_activated": effect.backup_activated is True,
        "backup_is_acceptable": effect.backup_tank_id in acceptable_backup_tank_ids,
        "surge_applied": (
            effect.surge_multiplier_applied is not None
            and effect.surge_multiplier_applied > 1.0
        ),
    }

    return checks, all(checks.values())


def score_allocation(result, expected_supplier_count: int = None, tolerance_ratio: float = 1e-4) -> tuple:
    """
    Checks the allocation actually adds up: total allocated equals
    what was requested (within a relative tolerance, since float
    division across suppliers won't sum to an exact bit-for-bit
    match), and normalized shares sum to 1.0. Both checks apply
    identically whether this was a plain split or a redistribution-
    around-an-unavailable-supplier scenario - the invariants don't
    change, only the inputs do.
    """

    total_allocated = sum(line.allocated_qty for line in result.allocations)
    tolerance = max(1e-6, result.total_qty_needed * tolerance_ratio)

    checks = {
        "total_matches_requested": abs(total_allocated - result.total_qty_needed) <= tolerance,
        "shares_sum_to_one": abs(
            sum(line.allocated_share_actual for line in result.allocations) - 1.0
        ) < 1e-6,
    }

    if expected_supplier_count is not None:
        checks["supplier_count_matches"] = len(result.allocations) == expected_supplier_count

    return checks, all(checks.values())


def score_shipment_delay(result, tank_id: str, expect_at_risk: bool) -> tuple:
    """
    Checks the at-risk flag matches expectation for this specific
    tank/delay-length pair (the actual boundary condition
    report_delay is built around), and - only when risk was expected
    - that a recommendation was actually produced rather than an
    empty string.
    """

    checks = {
        "at_risk_matches_expectation": (tank_id in result.tanks_at_risk) == expect_at_risk,
    }

    if expect_at_risk:
        checks["recommendation_produced"] = bool(result.recommended_action)

    return checks, all(checks.values())