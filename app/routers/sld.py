from typing import Literal
from fastapi import APIRouter, HTTPException, Query

from app.models.sld import (
    RFQ,
    ProductUnderlyingsResponse,
    ProductFeesResponse,
    Product,
    Underlying,
)
from app.services.sld_service import sld_service

router = APIRouter(prefix="/api/sld", tags=["sld"])


@router.get("/rfqs", response_model=list[RFQ])
def get_rfqs(
    rfq_id: str | None = Query(None, description="Filter by RFQ ID, ISIN, or product ID"),
    status: Literal["open", "quoted", "traded", "expired", "rejected"] | None = Query(
        None, description="Status filter"
    ),
    issuer: str | None = Query(None, description="Filter by issuer or quote provider"),
    product_type: str | None = Query(None, description="Filter by structured product type"),
    currency: str | None = Query(None, description="Filter by currency (e.g. CHF, USD, EUR)"),
    client: str | None = Query(None, description="Filter by client name"),
    limit: int = Query(10, ge=1, le=100, description="Max number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> list[RFQ]:
    """Fetch structured product RFQs from SLD."""
    return sld_service.get_rfqs(
        rfq_id=rfq_id,
        status=status,
        issuer=issuer,
        product_type=product_type,
        currency=currency,
        client=client,
        limit=limit,
        offset=offset,
    )


@router.get("/products", response_model=list[Product])
def get_products(
    product_id: str | None = Query(None, description="Filter by product ID"),
    isin: str | None = Query(None, description="Filter by ISIN"),
    product_type: str | None = Query(None, description="Filter by product type"),
    currency: str | None = Query(None, description="Filter by currency"),
    basket_type: str | None = Query(None, description="Filter by basket type"),
    status: str | None = Query(None, description="Filter by status"),
    client: str | None = Query(None, description="Filter by client name"),
    limit: int = Query(10, ge=1, le=100, description="Max number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> list[Product]:
    """Fetch structured products with their underlyings and fee structures."""
    return sld_service.get_products(
        product_id=product_id,
        isin=isin,
        product_type=product_type,
        currency=currency,
        basket_type=basket_type,
        status=status,
        client=client,
        limit=limit,
        offset=offset,
    )


@router.get("/products/{product_id}", response_model=Product)
def get_product_by_id(product_id: str) -> Product:
    """Fetch a single structured product by product ID, ISIN, or RFQ ID."""
    try:
        return sld_service.get_product_by_id(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/products/{product_id}/underlyings", response_model=ProductUnderlyingsResponse)
def get_underlyings_of_product(product_id: str) -> ProductUnderlyingsResponse:
    """Fetch underlyings for a product, ISIN, or RFQ."""
    try:
        return sld_service.get_underlyings_of_product(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/underlyings", response_model=ProductUnderlyingsResponse | list[Underlying])
def get_underlyings_query(
    product_id: str | None = Query(None, description="Product ID, ISIN, or RFQ ID"),
    ticker: str | None = Query(None, description="Filter by underlying ticker"),
    asset_class: str | None = Query(None, description="Filter by asset class"),
    currency: str | None = Query(None, description="Filter by currency"),
    barrier_hit: bool | None = Query(None, description="Filter by barrier hit status"),
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> ProductUnderlyingsResponse | list[Underlying]:
    """Query underlyings by product or by constituent criteria."""
    if product_id:
        try:
            return sld_service.get_underlyings_of_product(product_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
    return sld_service.get_underlyings(
        ticker=ticker,
        asset_class=asset_class,
        currency=currency,
        barrier_hit=barrier_hit,
        limit=limit,
        offset=offset,
    )


@router.get("/products/{product_id}/fees", response_model=ProductFeesResponse)
def get_fees_of_product(
    product_id: str,
    fee_type: str | None = Query(None, description="Fee filter (e.g. distribution, structuring)"),
) -> ProductFeesResponse:
    """Fetch fee structure for a product, ISIN, or RFQ."""
    try:
        return sld_service.get_fees_of_product(product_id, fee_type=fee_type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/fees", response_model=ProductFeesResponse | list[ProductFeesResponse])
def get_fees_query(
    product_id: str | None = Query(None, description="Product ID, ISIN, or RFQ ID"),
    currency: str | None = Query(None, description="Filter by currency"),
    max_total_fee_pct: float | None = Query(None, description="Max total fee percentage"),
    fee_type: str | None = Query(None, description="Fee filter"),
    limit: int = Query(10, ge=1, le=100, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> ProductFeesResponse | list[ProductFeesResponse]:
    """Query fee schedules by product or across products."""
    if product_id:
        try:
            return sld_service.get_fees_of_product(product_id, fee_type=fee_type)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
    return sld_service.get_fees(
        currency=currency,
        max_total_fee_pct=max_total_fee_pct,
        limit=limit,
        offset=offset,
    )
