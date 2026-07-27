import pandas as pd

def load_schedule_data():
    return pd.read_csv(r"E:/Supply_chain_agentic_ai/data/Supplier-Schedule.csv")

def load_info_data():
    return pd.read_csv(r"E:/Supply_chain_agentic_ai/data/Supplier-Info.csv")

def load_tank_master_data():
    return pd.read_csv(r"E:/Supply_chain_agentic_ai/data/Tanks-Master-Data.csv")

def load_consumption_data():
    return pd.read_csv(r"E:/Supply_chain_agentic_ai/data/Consumption-Data.csv")