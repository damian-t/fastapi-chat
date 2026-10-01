from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class RFQQuote(BaseModel):
    issuer: str
    price_pct: float = Field(..., description="Offered price in percentage of nominal")
    coupon_pct_pa: float = Field(..., description="Annualized coupon rate in %")
    timestamp: str
    valid_until: str


class RFQ(BaseModel):
    rfq_id: str
    product_id: str
    isin: str
    product_name: str
    product_type: str
    status: Literal["open", "quoted", "traded", "expired", "rejected"]
    currency: str
    nominal: float
    client: str
    underlyings: list[str]
    quotes: list[RFQQuote] = Field(default_factory=list)
    best_quote: RFQQuote | None = None
    traded_with: str | None = None
    traded_price_pct: float | None = None
    created_at: str
    expires_at: str


class Underlying(BaseModel):
    name: str
    ticker: str
    asset_class: str
    currency: str
    spot_price: float
    strike_level_pct: float
    barrier_level_pct: float | None = None
    current_price: float
    performance_pct: float
    barrier_hit: bool = False
    distance_to_barrier_pct: float | None = None
    product_id: str | None = None
    isin: str | None = None


class ProductUnderlyingsResponse(BaseModel):
    product_id: str
    isin: str
    product_name: str
    basket_type: str
    underlyings: list[Underlying]


class ProductFeesResponse(BaseModel):
    product_id: str
    isin: str
    product_name: str
    currency: str
    nominal: float
    distribution_fee_pct: float
    structuring_fee_pct: float
    management_fee_pct_pa: float
    exchange_fee_pct: float
    total_fee_pct: float
    estimated_monetary_amount: float
    description: str


class Product(BaseModel):
    product_id: str
    isin: str
    rfq_id: str
    product_name: str
    product_type: str
    basket_type: str
    status: str
    currency: str
    nominal: float
    client: str
    created_at: str
    expires_at: str
    traded_with: str | None = None
    traded_price_pct: float | None = None
    underlyings: list[Underlying] = Field(default_factory=list)
    fees: ProductFeesResponse | None = None
