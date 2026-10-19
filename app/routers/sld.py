from typing import Literal
from fastapi import APIRouter, HTTPException, Query

from app.models.sld import (
    Product,
    Underlying,
    Fee,
)
from app.services.sld_service import sld_service

router = APIRouter(prefix="/api/sld", tags=["sld"])


@router.get("/rfqs", response_model=list[Product])
@router.get("/products", response_model=list[Product])
def get_rfqs(
    start_date: str | None = Query(None, description="Start date of search period"),
    end_date: str | None = Query(None, description="End date for search period"),
    isin: str | None = Query(None, description="ISIN of the quoted product"),
    valor: str | None = Query(None, description="Valor of the quoted product"),
    currency: str | None = Query(None, description="Filter by currency (e.g. CHF, USD, EUR)"),
    status: Literal["open", "quoted", "traded", "expired", "rejected"] | None = Query(None, description="Status filter"),
    issuer: str | None = Query(None, description="Filter by quoting issuer"),
    product_type: str | None = Query(None, description="Filter by structured product type"),
    underlying: str | None = Query(None, description="Filter by underlying ticker"),
    rfq_id: str | None = Query(None, description="Filter by RFQ or product ID"),
    client: str | None = Query(None, description="Filter by client name"),
    limit: int | None = Query(None, ge=1, le=100, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[Product]:
    """Fetch structured products from SLD matching date range, identifiers, or subset filters. Returns a list of Product dataclasses."""
    return sld_service.get_rfqs(
        start_date=start_date,
        end_date=end_date,
        isin=isin,
        valor=valor,
        currency=currency,
        status=status,
        issuer=issuer,
        product_type=product_type,
        underlying=underlying,
        rfq_id=rfq_id,
        client=client,
        limit=limit,
        offset=offset,
    )


@router.get("/products/{product_id}/underlyings", response_model=list[Underlying])
def get_underlyings_for_product(product_id: str) -> list[Underlying]:
    """Fetch underlying Bloomberg tickers for a product, ISIN, or RFQ. Returns a list of Underlying dataclasses."""
    try:
        return sld_service.get_underlyings_for_product(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


get_underlyings_of_product = get_underlyings_for_product


@router.get("/underlyings", response_model=list[Underlying])
def get_underlyings_query(
    product_id: str = Query(..., description="Product ID, ISIN, or RFQ ID")
) -> list[Underlying]:
    """Alternative query endpoint for underlyings."""
    return get_underlyings_for_product(product_id)


@router.get("/products/{product_id}/fees", response_model=list[Fee])
def get_fees_for_product(
    product_id: str,
) -> list[Fee]:
    """Fetch fee structure for a product, ISIN, or RFQ. Returns a list of Fee dataclasses."""
    try:
        return sld_service.get_fees_for_product(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


get_fees_of_product = get_fees_for_product


@router.get("/fees", response_model=list[Fee])
def get_fees_query(
    product_id: str = Query(..., description="Product ID, ISIN, or RFQ ID"),
) -> list[Fee]:
    """Alternative query endpoint for product fees."""
    return get_fees_for_product(product_id)
