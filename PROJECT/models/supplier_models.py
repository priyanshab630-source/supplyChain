from pydantic import BaseModel

class SupplierResult(BaseModel):

    supplier_name: str
    tanks_served: int
    total_shipments: int
    total_shipment_qty: float
    avg_shipment_qty: float
    missed_shipments: int
    fill_rate: float
    reliability_score: float
    single_source_dependency: bool
    risk_level: str
    recommendation: str