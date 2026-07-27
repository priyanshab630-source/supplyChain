from langchain.tools import tool
from dotenv import load_dotenv
from PROJECT.agents.consumption_forecast_agent import ForecastAgent
load_dotenv()
from PROJECT.data_loader.loader import (load_consumption_data,load_tank_master_data)

consumption_df = load_consumption_data()
tank_df = load_tank_master_data()
forecast_agent = ForecastAgent(consumption_df)

@tool
def forecast_tool(tank_id: str) -> str:
    """
    Forecast future consumption for a tank.

    tank_id must be in the format:
    'Tank 1', 'Tank 2', 'Tank 34', etc.
    """

    tank_id = str(tank_id).strip()

    if tank_id.isdigit():
        tank_id = f"Tank {tank_id}"

    print("=" * 50)
    print("FORECAST TOOL CALLED")
    print("tank_id received:", repr(tank_id))
    print("=" * 50)

    result = forecast_agent.run(tank_id)
    return result.model_dump(mode="json")