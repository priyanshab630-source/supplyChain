from pydantic import BaseModel

class RiskResult(BaseModel):
    tank_id: str
    inventory_risk_score: int
    forecast_risk_score: int
    supplier_risk_score: int
    kg_risk_score: int
    overall_risk_score: int
    overall_risk_level: str
