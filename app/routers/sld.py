from typing import Literal
from fastapi import APIRouter, HTTPException, Query

from app.models.sld import (
    RFQ,
    ProductUnderlyingsResponse,
    ProductFeesResponse,
)
from app.services.sld_service import sld_service

router = APIRouter(prefix="/api/sld", tags=["sld"])


@router.get("/rfqs", response_model=list[RFQ])
def get_rfqs(
    rfq_id: str | None = Query(None, description="Filter by RFQ ID or ISIN"),
    status: Literal["open", "quoted", "traded", "expired", "rejected"] | None = Query(
        None, description="Status filter"
    ),
    issuer: str | None = Query(None, description="Filter by issuer or quote provider"),
    product_type: str | None = Query(None, description="Filter by structured product type"),
    currency: str | None = Query(None, description="Filter by currency (e.g. CHF, USD, EUR)"),
    limit: int = Query(10, ge=1, le=50, description="Max number of items to return"),
) -> list[RFQ]:
    """Fetch structured product RFQs from SLD."""
    return sld_service.get_rfqs(
        rfq_id=rfq_id,
        status=status,
        issuer=issuer,
        product_type=product_type,
        currency=currency,
        limit=limit,
    )


@router.get("/products/{product_id}/underlyings", response_model=ProductUnderlyingsResponse)
def get_underlyings_of_product(product_id: str) -> ProductUnderlyingsResponse:
    """Fetch underlyings for a product, ISIN, or RFQ."""
    try:
        return sld_service.get_underlyings_of_product(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/underlyings", response_model=ProductUnderlyingsResponse)
def get_underlyings_query(
    product_id: str = Query(..., description="Product ID, ISIN, or RFQ ID")
) -> ProductUnderlyingsResponse:
    """Alternative query endpoint for underlyings."""
    return get_underlyings_of_product(product_id)


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


@router.get("/fees", response_model=ProductFeesResponse)
def get_fees_query(
    product_id: str = Query(..., description="Product ID, ISIN, or RFQ ID"),
    fee_type: str | None = Query(None, description="Fee filter"),
) -> ProductFeesResponse:
    """Alternative query endpoint for product fees."""
    return get_fees_of_product(product_id, fee_type=fee_type)
