from pydantic import BaseModel, Field
from langchain.tools import tool
from dotenv import load_dotenv

from PROJECT.agents.inventory_agent import InventoryAgent

load_dotenv()

from PROJECT.data_loader.loader import load_consumption_data, load_tank_master_data
from PROJECT.tools.tank_id_utils import normalize_tank_id

consumption_df = load_consumption_data()
tank_df = load_tank_master_data()

inventory_agent = InventoryAgent(consumption_df, tank_df)


class InventoryLookupArgs(BaseModel):
    """
    Structured arg instead of a free-text question - same reasoning
    as SupplierLookupArgs: the model fills ONE typed field, it
    doesn't compose a sentence that then has to be regex-parsed a
    second time.
    """

    tank_id: str = Field(
        description=(
            "The tank id, e.g. 'Tank 1', 'Tank 15', 'Tank 34'. Copy it "
            "verbatim from the question. A bare number like '1' is "
            "also accepted and will be normalized automatically."
        ),
    )


@tool(args_schema=InventoryLookupArgs)
def inventory_risk_tool(tank_id: str) -> dict:
    """
    Analyze inventory risk for a tank: current level, consumption
    rate, days of cover, and risk tier.
    """

    tank_id = normalize_tank_id(tank_id)

    print("=" * 50)
    print("TOOL CALLED")
    print("tank_id received:", repr(tank_id))
    print("=" * 50)

    try:
        result = inventory_agent.run_for_tank(tank_id)  # clean path - no re-parsing
        return result.model_dump(mode="json")

    except Exception as exc:
        return {"error": str(exc)}