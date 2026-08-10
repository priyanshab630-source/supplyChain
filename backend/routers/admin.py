from fastapi import APIRouter

from PROJECT.data_loader.loader import refresh_all

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/refresh-data")
def refresh_data():
    """
    Clears the in-process cache of tank/supplier/consumption data, so
    the next request re-reads from the database instead of the values
    loaded at startup. Call this after updating the underlying tables
    (e.g. after re-running seed_from_csv.py or inserting rows
    directly), instead of restarting the server.
    """
    refresh_all()
    return {"status": "refreshed"}
