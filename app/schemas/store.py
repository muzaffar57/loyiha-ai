from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.store_enums import StoreProductType, StoreUnit


class CategoryRef(BaseModel):
    id: int
    name: str
    slug: str


class StoreCategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    image: str | None
    sort_order: int
    children: list["StoreCategoryOut"] = Field(default_factory=list)


class StoreCategoryDetail(StoreCategoryOut):
    parent: CategoryRef | None = None


class StoreCategoryList(BaseModel):
    items: list[StoreCategoryOut]


class StoreProductOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    sku: str | None
    images: list[str]
    product_type: StoreProductType
    unit: StoreUnit
    is_featured: bool
    category: CategoryRef
    dimensions: str | None = None
    selling_price: str | None = None
    available_quantity: int | None = None


class StoreProductPage(BaseModel):
    items: list[StoreProductOut]
    page: int
    page_size: int
    total: int


class StorePublicConfig(BaseModel):
    currency: str
    company_phone: str | None
    checkout_enabled: bool


def money_to_text(value: Decimal | int | float | str | None) -> str | None:
    if value is None:
        return None
    amount = Decimal(str(value))
    return format(amount, "f")
