from pydantic import BaseModel, Field

from app.services.mysldclient.products import (
    Underlying,
    ProductGeneral,
    ProductPricing,
    Fee,
    ProductFees,
    Product,
)


class MapReduceFilterParams(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    status: str | None = None
    currency: str | None = None
    issuer: str | None = None
    product_type: str | None = None
    underlying: str | None = None


class MapReduceRequest(BaseModel):
    filter_params: MapReduceFilterParams | None = None
    batch_size: int = Field(default=500, ge=1, le=5000, description="Server-side batch page size (default: 500)")
    operation: str = Field(default="summary", description="Analysis operation (e.g. 'summary')")


class NumberRange(BaseModel):
    min: float | None = None
    max: float | None = None


class TopProductSummary(BaseModel):
    rfq_id: str | None = None
    product_id: str | None = None
    isin: str | None = None
    name: str | None = None
    currency: str | None = None
    nominal: float = 0.0
    status: str | None = None


class MapReduceResponse(BaseModel):
    operation: str = "summary"
    batch_size: int = 500
    batches_processed: int = 0
    total_records_processed: int = 0
    total_nominal_volume: float = 0.0
    volumes_by_currency: dict[str, float] = Field(default_factory=dict)
    counts_by_currency: dict[str, int] = Field(default_factory=dict)
    status_distribution: dict[str, int] = Field(default_factory=dict)
    product_type_distribution: dict[str, int] = Field(default_factory=dict)
    volumes_by_issuer: dict[str, float] = Field(default_factory=dict)
    counts_by_issuer: dict[str, int] = Field(default_factory=dict)
    top_underlyings: dict[str, int] = Field(default_factory=dict)
    average_fair_value_pct: float | None = None
    fair_value_range: NumberRange = Field(default_factory=NumberRange)
    average_entry_costs_pct: float | None = None
    entry_costs_range: NumberRange = Field(default_factory=NumberRange)
    top_products_by_volume: list[TopProductSummary] = Field(default_factory=list)


__all__ = [
    "Underlying",
    "ProductGeneral",
    "ProductPricing",
    "Fee",
    "ProductFees",
    "Product",
    "MapReduceFilterParams",
    "MapReduceRequest",
    "MapReduceResponse",
]
