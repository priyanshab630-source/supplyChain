"""
Was duplicated identically in inventory_tools.py and
consumption_forcast_tools.py:

    tank_id = str(tank_id).strip()
    if tank_id.isdigit():
        tank_id = f"Tank {tank_id}"

One source of truth here instead - also used by
tank_id_normalizer_middleware.py so the same normalization happens
automatically for ANY tool with a tank_id arg, not just the two that
remembered to call this by hand.
"""


def normalize_tank_id(tank_id: str) -> str:
    tank_id = str(tank_id).strip()
    if tank_id.isdigit():
        tank_id = f"Tank {tank_id}"

    return tank_id