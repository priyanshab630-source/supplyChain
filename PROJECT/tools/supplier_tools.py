from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import tool
from PROJECT.agents.supplier_agent import SupplierAgent
from PROJECT.data_loader.loader import load_schedule_data, load_info_data

Schedule_df = load_schedule_data()
Info_df = load_info_data()
supplier_agent = SupplierAgent(Schedule_df, Info_df)


class SupplierLookupArgs(BaseModel):
    """
    Structured args instead of a free-text question. The LLM tool
    call has to fill these two typed fields, not compose a sentence -
    this is what was causing lookups like "Supplier dteials" to fail:
    the model was rewriting/garbling the question text before it ever
    reached the deterministic regex parser inside SupplierAgent.
    """

    supplier_name: Optional[str] = Field(
        default=None,
        description=(
            "The exact supplier name as it appears in the question, "
            "e.g. 'Supplier A'. Copy it verbatim - do not paraphrase "
            "or add/remove words. Leave empty if no supplier was named."
        ),
    )

    tank_id: Optional[str] = Field(
        default=None,
        description=(
            "The exact tank id as it appears in the question, e.g. "
            "'Tank 15'. Copy it verbatim. Leave empty if no tank was "
            "named."
        ),
    )


@tool(args_schema=SupplierLookupArgs)
def supplier_tool(
    supplier_name: Optional[str] = None,
    tank_id: Optional[str] = None,
):
    """
    Look up supplier reliability, shipment, and risk information.
    Provide EITHER a supplier_name OR a tank_id (to resolve that
    tank's supplier first) - never leave both empty.
    """

    if not supplier_name and tank_id:
        supplier_name = supplier_agent.get_supplier_for_tank(tank_id)
        if supplier_name is None:
            return {
                "error": f"{tank_id} does not have a supplier assigned in the current data."
            }
    if not supplier_name:
        return {"error": "No supplier name or tank id was provided."}

    try:
        result = supplier_agent.run_for_supplier(supplier_name)
        return result.model_dump(mode="json")
    except Exception as exc:
        return {"error": str(exc)}
