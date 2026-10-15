from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, List, Optional


@dataclass
class Underlying:
    underlyingBloombergTicker: str


@dataclass
class ProductGeneral:
    productId: int = None
    productUuid: Optional[str] = None
    partyIdentifierCustodian: Optional[str] = None
    partyIdentifierClient: Optional[str] = None
    productType: Optional[str] = None
    productAmount: Optional[float] = None
    productQuotationType: Optional[str] = None
    currency: Optional[str] = None
    initialFixingType: Optional[str] = None
    initialFixingDate: Optional[str] = None
    finalFixingDate: Optional[str] = None
    issueDate: Optional[str] = None
    finalPaymentDate: Optional[str] = None
    underlyingList: List[Underlying] = field(default_factory=list)
    dayCountFraction: Optional[str] = None
    settlementType: Optional[str] = None
    finalValuationCutOffTime: Optional[str] = None
    finalValuationCutOffLocation: Optional[str] = None
    productName: Optional[str] = None
    valor: Optional[str] = None
    isin: Optional[str] = None


@dataclass
class ProductPricing:
    fairValue: Decimal


@dataclass
class Fee:
    name: str
    amount: float
    feeType: str
    maturityType: str
    isPricingRelevant: bool


@dataclass
class ProductFees:
    entryCosts: Decimal
    _product_id: int = field(repr=False)

    def get_fees(self, backend: Any = None) -> List[Fee]:
        """Lazy-load underlyings for this product using the backend."""
        if backend and hasattr(backend, "get_fees_for_product"):
            return backend.get_fees_for_product(product_id=self._product_id)
        return []


@dataclass
class Product:
    productGeneral: ProductGeneral
    productPricing: ProductPricing
    productFees: ProductFees
    _status: Optional[str] = field(default=None, repr=False)
    _quotes: List[Any] = field(default_factory=list, repr=False)
    # todo Add other sections as needed (productYield, productCall, etc.)

    def get_underlyings(self, backend: Any = None) -> List[Underlying]:
        """Lazy-load underlyings for this product using the backend."""
        if backend and hasattr(backend, "get_underlyings_for_product"):
            return backend.get_underlyings_for_product(product_id=self.productGeneral.productId)
        return self.productGeneral.underlyingList

    @property
    def rfq_id(self) -> str:
        return f"RFQ-{self.productGeneral.productId}" if self.productGeneral.productId else ""

    @property
    def product_id(self) -> str:
        return self.productGeneral.productUuid or (f"PRD-{self.productGeneral.productId}" if self.productGeneral.productId else "")

    @property
    def isin(self) -> str:
        return self.productGeneral.isin or ""

    @property
    def product_name(self) -> str:
        return self.productGeneral.productName or ""

    @property
    def currency(self) -> str:
        return self.productGeneral.currency or ""

    @property
    def nominal(self) -> float:
        return self.productGeneral.productAmount or 0.0

    @property
    def product_type(self) -> str:
        return self.productGeneral.productType or ""

    @property
    def client(self) -> str:
        return self.productGeneral.partyIdentifierClient or ""

    @property
    def status(self) -> str:
        return self._status or "open"

    @property
    def quotes(self) -> List[Any]:
        return self._quotes
