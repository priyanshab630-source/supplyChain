from pydantic import BaseModel, Field
from langchain.tools import tool
from dotenv import load_dotenv

from PROJECT.agents.consumption_forecast_agent import ForecastAgent

load_dotenv()

from PROJECT.data_loader.loader import load_consumption_data, load_tank_master_data
from PROJECT.tools.tank_id_utils import normalize_tank_id

consumption_df = load_consumption_data()
tank_df = load_tank_master_data()

forecast_agent = ForecastAgent(consumption_df)


class ForecastLookupArgs(BaseModel):
    """Structured arg - same reasoning as InventoryLookupArgs / SupplierLookupArgs."""

    tank_id: str = Field(
        description=(
            "The tank id, e.g. 'Tank 1', 'Tank 15', 'Tank 34'. Copy it "
            "verbatim from the question. A bare number like '1' is "
            "also accepted and will be normalized automatically."
        ),
    )


@tool(args_schema=ForecastLookupArgs)
def forecast_tool(tank_id: str) -> dict:
    """
    Forecast future consumption for a tank: 7/30-day averages,
    next-day and next-week projections, predicted stockout date.
    """

    tank_id = normalize_tank_id(tank_id)

    print("=" * 50)
    print("FORECAST TOOL CALLED")
    print("tank_id received:", repr(tank_id))
    print("=" * 50)

    try:
        result = forecast_agent.run_for_tank(tank_id)  # clean path - no re-parsing
        return result.model_dump(mode="json")

    except Exception as exc:
        return {"error": str(exc)}