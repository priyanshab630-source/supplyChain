import json
from langchain_core.messages import AIMessage, ToolMessage
from PROJECT.state.agent_state import SupplyChainState
from PROJECT.models.inventory_models import InventoryResult
from PROJECT.models.consumption_forecast_models import ConsumptionForecastResult
from PROJECT.models.supplier_models import SupplierResult
from PROJECT.models.kg_models import KGResult
from PROJECT.orchestrators.inventory_orchestrator import build_inventory_agent
from PROJECT.orchestrators.consumption_orchestrator import build_forecast_agent
from PROJECT.orchestrators.supplier_orchestrator import build_supplier_agent
from PROJECT.agents.kg_agent import kg_agent
from PROJECT.agents.risk_manager_agent import RiskAgent
from PROJECT.agents.recommendation_agent import RecommendationAgent
from PROJECT.tools.inventory_tools import (
    inventory_agent as inventory_engine,
    tank_df as tank_master_df,
)
from PROJECT.tools.consumption_forcast_tools import forecast_agent as forecast_engine
from PROJECT.tools.supplier_tools import supplier_agent as supplier_engine
from PROJECT.graph.prompts import FINAL_ANSWER_PROMPT
from PROJECT.llm.groq import get_groq_model

risk_agent = RiskAgent()
recommendation_agent = RecommendationAgent()

final_answer_llm = get_groq_model()
final_answer_chain = FINAL_ANSWER_PROMPT | final_answer_llm


inventory_agent = build_inventory_agent()
forecast_agent = build_forecast_agent()
supplier_agent = build_supplier_agent()


def update_completed(state: SupplyChainState, agent_name: str):
    completed = list(state.get("completed_agents", []))
    if agent_name not in completed:
        completed.append(agent_name)

    return completed


def append_error(state: SupplyChainState, error):
    """
    Append a new error message (if any) to the running list of
    errors in state, so missing/invalid data (tank not found,
    supplier not found, no consumption history, etc.) is
    surfaced in the final answer instead of silently vanishing.
    """

    errors = list(state.get("errors", []))
    if error:
        errors.append(error)

    return errors


def extract_tool_result(agent_output):
    if agent_output is None:
        return None

    if not isinstance(agent_output, dict):
        return None

    messages = agent_output.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            content = message.content
            if isinstance(content, dict):
                return content
            if isinstance(content, str):
                try:
                    return json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    continue

    return None


# Inventory
def inventory_node(state: SupplyChainState):

    print("\n========== INVENTORY NODE ==========")
    print("=" * 60)
    print("Running Inventory Node")
    print("=" * 60)

    try:
        if state.get("tank_id"):
            result = inventory_engine.run(f"show inventory of {state['tank_id']}")
            error = None

        else:
            agent_output = inventory_agent.run(state["question"])
            payload = extract_tool_result(agent_output)
            result = InventoryResult(**payload) if payload else None
            error = None if result is not None else "Inventory data could not be retrieved."

    except Exception as exc:
        result = None
        error = str(exc)
        print(f"Inventory node error: {error}")

    return {
        "messages": [
            AIMessage(content="Inventory analysis completed.")
        ],

        "inventory": result,
        "errors": append_error(state, error),
        "completed_agents": update_completed(state, "inventory"),
        "next_agent": "supervisor",
    }


# Forecast
def forecast_node(state: SupplyChainState):
    print("\n========== FORECAST NODE ==========")
    print("=" * 60)
    print("Running Forecast Node")
    print("=" * 60)

    try:
        if state.get("tank_id"):
            result = forecast_engine.run(f"forecast consumption for {state['tank_id']}")
            error = None

        else:
            agent_output = forecast_agent.run(state["question"])
            payload = extract_tool_result(agent_output)
            result = ConsumptionForecastResult(**payload) if payload else None
            error = None if result is not None else "Forecast data could not be retrieved."

    except Exception as exc:
        result = None
        error = str(exc)
        print(f"Forecast node error: {error}")

    return {
        "messages": [
            AIMessage(content="Forecast completed.")
        ],
        "forecast": result,
        "errors": append_error(state, error),
        "completed_agents": update_completed(state, "forecast"),
        "next_agent": "supervisor",
    }


# Supplier
def supplier_node(state: SupplyChainState):
    print("\n========== SUPPLIER NODE ==========")
    print("=" * 60)
    print("Running Supplier Node")
    print("=" * 60)

    try:
        if state.get("tank_id") or state.get("supplier_name"):

            supplier_name = state.get("supplier_name")
            tank_id = state.get("tank_id")

            if not supplier_name and tank_id:
                supplier_name = supplier_engine.get_supplier_for_tank(tank_id)

                if supplier_name is None:
                    raise ValueError(
                        f"{tank_id} does not have a supplier assigned in the current data."
                    )

            result = supplier_engine.run_for_supplier(supplier_name)
            error = None

        else:
            agent_output = supplier_agent.run(state["question"])
            payload = extract_tool_result(agent_output)
            result = SupplierResult(**payload) if payload else None
            error = None if result is not None else "Supplier data could not be retrieved."

    except Exception as exc:
        result = None
        error = str(exc)
        print(f"Supplier node error: {error}")

    return {
        "messages": [
            AIMessage(content="Supplier analysis completed.")
        ],
        "supplier": result,
        "errors": append_error(state, error),
        "completed_agents": update_completed(state, "supplier"),
        "next_agent": "supervisor",
    }


# Knowledge Graph
def kg_node(state: SupplyChainState):
    print("\n========== KG NODE ==========")
    print("=" * 60)
    print("Running KG Node")
    print("=" * 60)

    try:
        result = kg_agent.run(question=state["question"])
        error = None if result is not None else "Knowledge graph data could not be retrieved."

    except Exception as exc:
        result = None
        error = str(exc)
        print(f"KG node error: {error}")

    return {
        "messages": [
            AIMessage(
                content="Knowledge Graph analysis completed."
            )
        ],
        "kg": result,
        "errors": append_error(state, error),
        "completed_agents": update_completed(state, "kg"),
        "next_agent": "supervisor",
    }


MAX_NETWORK_TANKS = 30


def _resolve_target_tanks(state: SupplyChainState):
    """
    Decide which tanks this question is actually about.

    Returns (tank_ids, scope_label, resolve_error).

    1. A supplier was named ("tanks Supplier B supplies", "what's
       affected if Supplier B fails") -> use the supplier's tanks.
       If NOTHING matches that supplier name, this does NOT
       silently fall back to every tank - that would silently
       answer a different question than the one asked. It returns
       an empty list plus a clear resolve_error instead.
    2. No supplier named -> fall back to every known tank (a
       genuinely "prioritize across everything" question).
    """

    supplier_name = state.get("supplier_name")

    if supplier_name:
        tanks = supplier_engine.get_supplier_tanks(supplier_name)

        if tanks:
            return tanks, f"tanks supplied by {supplier_name}", None

        return (
            [],
            f"tanks supplied by {supplier_name}",
            f"No tanks were found for supplier '{supplier_name}' in the "
            "supplier/tank master data. Check the spelling, or whether "
            "that supplier exists in Info_df.",
        )

    all_tanks = (tank_master_df["tank_id"].dropna().unique().tolist())
    return all_tanks, "all known tanks", None


def _analyze_single_tank(tank_id: str):
    """
    Run the deterministic inventory + forecast engines for one tank
    and reduce the result to the fields needed for ranking. Returns
    a dict with an "error" key instead of raising, so one bad tank
    doesn't abort the whole fan-out.
    """

    try:
        inventory = inventory_engine.run(tank_id)

    except Exception as exc:
        return {"tank_id": tank_id, "error": str(exc)}

    try:
        forecast = forecast_engine.run(tank_id)

    except Exception:
        forecast = None

    inventory_risk = risk_agent.calculate_inventory_risk(inventory)
    forecast_risk = risk_agent.calculate_forecast_risk(forecast)
    combined_score = min(inventory_risk + forecast_risk, 100)

    return {
        "tank_id": tank_id,
        "gas": inventory.gas,
        "risk_level": inventory.risk_level,
        "risk_score": combined_score,
        "days_of_cover": inventory.days_of_cover,
        "current_inventory": inventory.current_inventory,
        "predicted_stockout_date": inventory.predicted_stockout_date,
    }


def network_node(state: SupplyChainState):
    print("\n========== NETWORK NODE ==========")
    print("=" * 60)
    print("Running Network Node")
    print("=" * 60)
    results = []
    scope_label = None
    error = None

    try:
        tank_ids, scope_label, resolve_error = _resolve_target_tanks(state)

        if resolve_error:
            error = resolve_error

        else:
            tank_ids = tank_ids[:MAX_NETWORK_TANKS]
            per_tank_errors = []

            for tank_id in tank_ids:
                analyzed = _analyze_single_tank(tank_id)
                if "error" in analyzed:
                    per_tank_errors.append(f"{tank_id}: {analyzed['error']}")
                else:
                    results.append(analyzed)

            results.sort(key=lambda r: (-r["risk_score"],r["days_of_cover"] if r["days_of_cover"] is not None else float("inf"),))
            if per_tank_errors:
                error = (f"Could not analyze {len(per_tank_errors)} tank(s) " f"while scanning {scope_label}: " + "; ".join(per_tank_errors))

            if not results and not error:
                error = f"No tanks could be resolved for {scope_label}."

    except Exception as exc:
        error = str(exc)
        print(f"Network node error: {error}")

    return {
        "messages": [
            AIMessage(content="Multi-tank network analysis completed.")
        ],
        "network_results": results,
        "network_scope": scope_label,
        "errors": append_error(state, error),
        "completed_agents": update_completed(state,"network"),
        "next_agent": "supervisor",
    }


# Risk
def risk_node(state: SupplyChainState):
    print("\n========== RISK NODE ==========")
    print("=" * 60)
    print("Running Risk Node")
    print("=" * 60)
    try:
        result = risk_agent.run(state)
        error = None

    except Exception as exc:
        result = None
        error = str(exc)
        print(f"Risk node error: {error}")

    return {
        "messages": [
            AIMessage(
                content="Risk analysis completed."
            )
        ],
        "risk": result,
        "errors": append_error(state, error),
        "completed_agents": update_completed(state, "risk"),
        "next_agent": "supervisor",
    }


# Recommendation
def recommendation_node(state: SupplyChainState):
    print("\n========== RECOMMENDATION NODE ==========")
    print("=" * 60)
    print("Running Recommendation Node")
    print("=" * 60)

    try:
        result = recommendation_agent.run(state)
        error = None

    except Exception as exc:
        result = None
        error = str(exc)
        print(f"Recommendation node error: {error}")

    return {
        "messages": [
            AIMessage(
                content="Recommendation generated."
            )
        ],
        "recommendation": result,
        "errors": append_error(state, error),
        "completed_agents": update_completed(state,"recommendation"),
        "next_agent": "supervisor",
    }


MAX_SECTION_CHARS = 1200


def truncate_text(text: str, max_chars: int = MAX_SECTION_CHARS) -> str:
    text = str(text)
    if len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip() + "\n... (truncated)"


def _format_network_results(network_results, limit=15) -> str:
    lines = []
    for r in network_results[:limit]:
        if r.get("days_of_cover") is not None:
            cover = f"{r['days_of_cover']:.2f} days of cover"
        else:
            cover = "no cover data"

        lines.append(f"- {r['tank_id']} ({r.get('gas', '?')}): "f"{r['risk_level']} risk, {cover}, "f"risk score {r['risk_score']}")

    if len(network_results) > limit:
        lines.append(f"... and {len(network_results) - limit} more tank(s).")

    return "\n".join(lines)


def build_final_answer_context(state: SupplyChainState) -> str:
    sections = []
    inventory = state.get("inventory")
    if inventory is not None:
        sections.append(f"Inventory Analysis:\n{truncate_text(inventory)}")

    forecast = state.get("forecast")
    if forecast is not None:
        sections.append(f"Forecast Analysis:\n{truncate_text(forecast)}")

    supplier = state.get("supplier")
    if supplier is not None:
        sections.append(f"Supplier Analysis:\n{truncate_text(supplier)}")

    kg = state.get("kg")
    if kg is not None:
        kg_summary = f"Question interpreted as: {kg.question}\nInsights: {kg.insights}"
        sections.append(f"Knowledge Graph Analysis:\n{truncate_text(kg_summary)}")

    network_results = state.get("network_results")
    if network_results:
        scope_label = state.get("network_scope") or "the relevant tanks"
        formatted = _format_network_results(network_results)
        sections.append(
            f"Network / Multi-Tank Analysis for {scope_label} (ranked by urgency):\n{truncate_text(formatted)}"
        )

    risk = state.get("risk")
    if risk is not None:
        sections.append(f"Risk Assessment:\n{truncate_text(risk)}")

    recommendation = state.get("recommendation")
    if recommendation is not None:
        sections.append(f"Recommendation:\n{truncate_text(recommendation)}")

    errors = state.get("errors")
    if errors:
        joined = "\n".join(f"- {e}" for e in errors)
        sections.append(f"Errors encountered while gathering data:\n{joined}")

    if not sections:
        return "No agent results were computed for this question."

    return "\n\n".join(sections)


def final_answer_node(state: SupplyChainState):
    print("\n========== FINAL ANSWER NODE ==========")
    print("=" * 60)
    print("Generating Final Answer")
    print("=" * 60)
    context = build_final_answer_context(state)
    response = final_answer_chain.invoke(
        {
            "question": state["question"],
            "context": context,
        }
    )
    answer = response.content
    return {
        "messages": [
            AIMessage(content=answer)
        ],
        "final_answer": answer,
        "next_agent": "end",
    }
