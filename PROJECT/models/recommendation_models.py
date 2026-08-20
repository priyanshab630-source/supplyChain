from pydantic import BaseModel


class Recommendation(BaseModel):
    tank_id: str
    recommended_action: str
    recommended_supplier: str | None
    recommended_order_qty: float | None
    recommended_delivery_date: str | None
    priority: str
    reasoning: str