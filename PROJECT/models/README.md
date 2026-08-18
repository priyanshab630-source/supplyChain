# PROJECT/models/

## Why this exists
One Pydantic model per agent's return type. Every agent in `agents/`
returns one of these instead of a raw dict — this is what makes
`result.model_dump(mode="json")` work uniformly across every tool in
`tools/`, and what lets `graph/nodes.py` reconstruct a result from a
dict (`InventoryResult(**payload)`) after it's been through JSON on
the wire.

## Files (one per agent, inferred from constructor calls across the codebase)
| File | Model | Used by |
|---|---|---|
| `inventory_models.py` | `InventoryResult` | `InventoryAgent`, `tools/tank_status_tools.py`'s surge adjustment |
| `consumption_forecast_models.py` | `ConsumptionForecastResult` | `ForecastAgent` |
| `supplier_models.py` | `SupplierResult` | `SupplierAgent` |
| `kg_models.py` | `KGResult` | `KGAgent` |
| `risk_models.py` | `RiskResult` | `RiskAgent` |
| `recommendation_models.py` | `Recommendation` | `RecommendationAgent` |
| `malfunction_models.py` | `MalfunctionResult` (P2) | `MalfunctionAgent` |
| `allocation_models.py` | `AllocationResult`, `SupplierAllocationLine` (P3) | `AllocationAgent`, reused by `ShipmentDelayAgent`'s reallocation |
| `shipment_models.py` | `ShipmentDelayResult`, `TankDelayImpact` (P4) | `ShipmentDelayAgent` |

## Convention
`state/agent_state.py`'s `SupplyChainState` types every result field
against one of these (`inventory: Optional[InventoryResult]`, etc.) —
adding a new agent means adding both the model here and the state
field, not just the agent class itself.
