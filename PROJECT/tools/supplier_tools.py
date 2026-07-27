from langchain.tools import tool
import json
from langchain.agents import create_agent
import os
from dotenv import load_dotenv

from PROJECT.agents.supplier_agent import SupplierAgent
load_dotenv()


from PROJECT.data_loader.loader import (
    load_info_data,
    load_schedule_data,
)

Schedule_df = load_schedule_data()
Info_df = load_info_data()


supplier_agent = SupplierAgent(
    Schedule_df,
    Info_df
)

@tool
def supplier_risk_tool(
    supplier_name: str
) -> str:
    """
    Analyze supplier performance and risk.

    Examples:
    Supplier A
    Supplier B
    Supplier C
    """

    supplier_name = str(
        supplier_name
    ).strip()

    print("=" * 50)
    print("SUPPLIER TOOL CALLED")
    print("supplier_name:", repr(supplier_name))
    print("=" * 50)

    result = supplier_agent.run(
        supplier_name
    )

    return result.model_dump(
        mode="json"
    )
