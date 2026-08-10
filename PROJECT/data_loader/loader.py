"""
Loads tank/supplier/consumption data from the database instead of
static CSVs, with a simple in-process cache so every agent call
doesn't re-hit the DB. Call refresh_all() (or hit the backend's
POST /api/admin/refresh-data endpoint) after the underlying tables
change, instead of restarting the process - that's what makes this
genuinely "dynamic" rather than just "moved the CSV into a database."
"""

import pandas as pd

from PROJECT.database.postgres import data_engine

_cache = {}


def _load(table_name: str, force_refresh: bool = False) -> pd.DataFrame:

    if force_refresh or table_name not in _cache:
        _cache[table_name] = pd.read_sql_table(table_name, data_engine)

    # Return a copy - callers (InventoryAgent, SupplierAgent, ...)
    # add/mutate columns on the DataFrames they're given (delta,
    # consumption, shipment_qty) and must not corrupt the shared cache.
    return _cache[table_name].copy()


def load_tank_master_data(force_refresh: bool = False) -> pd.DataFrame:
    return _load("tank_master", force_refresh)


def load_info_data(force_refresh: bool = False) -> pd.DataFrame:
    return _load("supplier_info", force_refresh)


def load_consumption_data(force_refresh: bool = False) -> pd.DataFrame:
    return _load("consumption_readings", force_refresh)


def load_schedule_data(force_refresh: bool = False) -> pd.DataFrame:
    return _load("supplier_schedule", force_refresh)


def refresh_all():
    _cache.clear()
