"""
Loads tank/supplier/consumption data from the database instead of
static CSVs, with a simple in-process cache so every agent call
doesn't re-hit the DB. Call refresh_all() (or hit the backend's
POST /api/admin/refresh-data endpoint) after the underlying tables
change, instead of restarting the process - that's what makes this
genuinely "dynamic" rather than just "moved the CSV into a database."
"""

import datetime

import pandas as pd
from sqlalchemy import text

from PROJECT.database.postgres import data_engine

import uuid
import json

_cache = {}


def _load(table_name: str, force_refresh: bool = False) -> pd.DataFrame:
    if force_refresh or table_name not in _cache:
        _cache[table_name] = pd.read_sql_table(table_name, data_engine)

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


_TANK_STATUS_DDL = """
CREATE TABLE IF NOT EXISTS tank_status (
    tank_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    surge_multiplier REAL NOT NULL DEFAULT 1.0,
    compensating_for TEXT,
    updated_at TEXT
)
"""
 
_UNSET = object()  


def _ensure_tank_status_table():
    with data_engine.begin() as conn:
        conn.execute(text(_TANK_STATUS_DDL))

    try:
        with data_engine.begin() as conn:
            conn.execute(text("ALTER TABLE tank_status ADD COLUMN compensating_for TEXT"))
    except Exception:
        pass  
 
 
def load_tank_status(force_refresh: bool = False) -> pd.DataFrame:
    _ensure_tank_status_table()
    return _load("tank_status", force_refresh)
 
 
def write_tank_status(
    tank_id: str,
    status: str,
    surge_multiplier: float = 1.0,
    compensating_for=_UNSET,
):
    """
    Upserts one tank's operational status.
 
    compensating_for is intentionally NOT a plain keyword defaulting
    to None - most call sites (initial seeding, marking a tank
    MALFUNCTION, a plain status refresh) aren't making any claim
    about who this tank covers for, and a plain None default would
    silently WIPE an existing compensating_for value on every one of
    those unrelated writes. Leave it unset to preserve whatever's
    already there (or NULL, for a brand-new row); pass a tank_id to
    claim it (malfunction_agent does this when activating a backup);
    pass None explicitly to CLEAR it (the simulator does this on
    recovery).
    """
 
    _ensure_tank_status_table()
    now = datetime.datetime.utcnow().isoformat()
 
    with data_engine.begin() as conn:
        if compensating_for is _UNSET:
            conn.execute(text(
                    """
                    INSERT INTO tank_status (tank_id, status, surge_multiplier, compensating_for, updated_at)
                    VALUES (:tank_id, :status, :surge_multiplier, NULL, :updated_at)
                    ON CONFLICT (tank_id) DO UPDATE SET
                        status = excluded.status,
                        surge_multiplier = excluded.surge_multiplier,
                        updated_at = excluded.updated_at
                    """
                ),
                {
                    "tank_id": tank_id,
                    "status": status,
                    "surge_multiplier": surge_multiplier,
                    "updated_at": now,
                },
            )
        else:
            conn.execute(text(
                    """
                    INSERT INTO tank_status (tank_id, status, surge_multiplier, compensating_for, updated_at)
                    VALUES (:tank_id, :status, :surge_multiplier, :compensating_for, :updated_at)
                    ON CONFLICT (tank_id) DO UPDATE SET
                        status = excluded.status,
                        surge_multiplier = excluded.surge_multiplier,
                        compensating_for = excluded.compensating_for,
                        updated_at = excluded.updated_at
                    """
                ),
                {
                    "tank_id": tank_id,
                    "status": status,
                    "surge_multiplier": surge_multiplier,
                    "compensating_for": compensating_for,
                    "updated_at": now,
                },
            )
 
    refresh_all()
 
 
def get_backup_for(tank_id: str):
    """
    Returns the tank currently compensating for tank_id, or None.
    This is what lets the simulator's tank-recovery command resolve
    the backup automatically instead of requiring --backup.
    """
    status_df = load_tank_status(force_refresh=True)
 
    if "compensating_for" not in status_df.columns:
        return None 
 
    rows = status_df.loc[status_df["compensating_for"] == tank_id, "tank_id"]
    return rows.iloc[0] if not rows.empty else None



_SHIPMENT_STATUS_DDL = """
CREATE TABLE IF NOT EXISTS shipment_status (
    supplier_name TEXT NOT NULL,
    tank_id TEXT NOT NULL,
    status TEXT NOT NULL,
    delay_days INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT,
    PRIMARY KEY (supplier_name, tank_id)
)
"""


def _ensure_shipment_status_table():
    with data_engine.begin() as conn:
        conn.execute(text(_SHIPMENT_STATUS_DDL))


def load_shipment_status(force_refresh: bool = False) -> pd.DataFrame:
    _ensure_shipment_status_table()
    return _load("shipment_status", force_refresh)


def write_shipment_status(
    supplier_name: str,
    tank_id: str,
    delay_days: int,
    status: str = "DELAYED",
):
    """
    Upserts one (supplier, tank) shipment's delay status. Mirrors
    write_tank_status's upsert pattern exactly, just on a composite
    key instead of a single tank_id, since one supplier can have an
    independent delay situation per tank it serves.
    """

    _ensure_shipment_status_table()

    with data_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO shipment_status
                    (supplier_name, tank_id, status, delay_days, updated_at)
                VALUES
                    (:supplier_name, :tank_id, :status, :delay_days, :updated_at)
                ON CONFLICT (supplier_name, tank_id) DO UPDATE SET
                    status = excluded.status,
                    delay_days = excluded.delay_days,
                    updated_at = excluded.updated_at
                """
            ),
            {
                "supplier_name": supplier_name,
                "tank_id": tank_id,
                "status": status,
                "delay_days": delay_days,
                "updated_at": datetime.datetime.utcnow().isoformat(),
            },
        )

    refresh_all()


def clear_shipment_delay(supplier_name: str, tank_id: str):
    """Marks a (supplier, tank) shipment back to on-time, e.g. once the delayed delivery lands."""
    write_shipment_status(supplier_name, tank_id, delay_days=0, status="ON_TIME")
    

_EVENT_LOG_DDL = """
CREATE TABLE IF NOT EXISTS event_log (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    details TEXT,
    created_at TEXT
)
"""


def _ensure_event_log_table():
    with data_engine.begin() as conn:
        conn.execute(text(_EVENT_LOG_DDL))


def load_event_log(force_refresh: bool = False) -> pd.DataFrame:
    _ensure_event_log_table()
    return _load("event_log", force_refresh)


def write_event_log(event_type: str, details: dict):
    """
    Append-only audit trail of every simulated (or, later, real)
    event the system has reacted to - a plain TEXT primary key
    (uuid) instead of an auto-increment int, so this works
    identically whether DATA_DATABASE_URL is sqlite or Postgres.
    Never upserts; every call is a new row.
    """

    _ensure_event_log_table()

    with data_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO event_log (event_id, event_type, details, created_at)
                VALUES (:event_id, :event_type, :details, :created_at)
                """
            ),
            {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "details": json.dumps(details, default=str),
                "created_at": datetime.datetime.utcnow().isoformat(),
            },
        )

    refresh_all()



_EVAL_RESULTS_DDL = """
CREATE TABLE IF NOT EXISTS eval_results (
    eval_run_id TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    created_at TEXT
)
"""
 
 
def _ensure_eval_results_table():
    with data_engine.begin() as conn:
        conn.execute(text(_EVAL_RESULTS_DDL))
 
 
def load_eval_results(force_refresh: bool = False) -> pd.DataFrame:
    """
    Every past eval run, most recent last by created_at. This is what
    makes P8 comparable OVER TIME instead of a single printout you
    have to remember or screenshot - re-run the suite after a code
    change and diff this against the previous run's summary.
    """
    _ensure_eval_results_table()
    return _load("eval_results", force_refresh)
 
 
def write_eval_run(eval_run_id: str, summary: dict):
    _ensure_eval_results_table()
 
    with data_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO eval_results (eval_run_id, summary, created_at)
                VALUES (:eval_run_id, :summary, :created_at)
                """
            ),
            {
                "eval_run_id": eval_run_id,
                "summary": json.dumps(summary, default=str),
                "created_at": datetime.datetime.utcnow().isoformat(),
            },
        )
 
    refresh_all()
 