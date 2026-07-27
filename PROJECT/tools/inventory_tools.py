from langchain.tools import tool
from dotenv import load_dotenv
from PROJECT.agents.inventory_agent import InventoryAgent
load_dotenv()
from PROJECT.data_loader.loader import (load_consumption_data, load_tank_master_data)

consumption_df = load_consumption_data()
tank_df = load_tank_master_data()


inventory_agent = InventoryAgent(consumption_df,tank_df)

@tool
def inventory_risk_tool(tank_id: str) -> str:
    """
    Analyze inventory risk.

    tank_id must be in the format:
    'Tank 1', 'Tank 2', 'Tank 34', etc.
    """

    tank_id = str(tank_id).strip()

    if tank_id.isdigit():
        tank_id = f"Tank {tank_id}"

    print("=" * 50)
    print("TOOL CALLED")
    print("tank_id received:", repr(tank_id))
    print("=" * 50)
    result = inventory_agent.run(tank_id)

    return result.model_dump(mode="json")