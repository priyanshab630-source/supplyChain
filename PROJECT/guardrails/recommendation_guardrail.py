"""
Defense-in-depth check on RecommendationAgent's output.
recommend_action() already only ever returns from a fixed set of
strings by construction - this guardrail doesn't trust that
invariant to hold forever (e.g. someone adds a new risk tier later
and forgets to update recommend_action()'s branches to match) and
validates at the boundary instead of trusting internal code shape.
"""

from PROJECT.guardrails.exceptions import GuardrailViolation

ALLOWED_ACTIONS = {
    "Emergency Reorder",
    "Place Replenishment Order",
    "Monitor Inventory",
    "Insufficient Data - Unable to Recommend",
    "No Action Required",
}


def validate_recommendation(recommendation):
    if recommendation.recommended_action not in ALLOWED_ACTIONS:
        raise GuardrailViolation(
            "recommendation_guardrail",
            f"Unrecognized recommended_action: '{recommendation.recommended_action}' "
            "is not in the allowed action set - refusing to return an unvalidated "
            "recommendation.",
        )