from pydantic import BaseModel


class SupplierAllocationLine(BaseModel):

    supplier_name: str
    contract_share: float
    allocated_qty: float
    allocated_share_actual: float


class AllocationResult(BaseModel):

    gas: str
    total_qty_needed: float
    allocations: list[SupplierAllocationLine]
    reasoning: str
