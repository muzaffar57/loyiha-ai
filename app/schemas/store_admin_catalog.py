"""Do‘kon administratori katalogi.

Narx, qoldiq, narx qoidasi, umumiy foiz va rasm yo‘li bu sxemada yo‘q.
Rasm faqat yuklash va o‘chirish endpointlari orqali biriktiriladi.
"""
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.store_enums import StoreProductType, StoreUnit

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SKU = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _clean_slug(value: str, *, limit: int) -> str:
    text = value.strip().lower()
    if not text or len(text) > limit or not _SLUG.fullmatch(text):
        raise ValueError("Slug faqat kichik harf, raqam va chiziqdan iborat bo‘lishi kerak.")
    return text


def _clean_sku(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if not _SKU.fullmatch(text):
        raise ValueError("SKU noto‘g‘ri.")
    return text


class AdminCategoryOut(BaseModel):
    id: int
    parent_id: int | None
    name: str
    slug: str
    description: str | None
    image: str | None
    is_active: bool
    sort_order: int


class AdminCategoryList(BaseModel):
    items: list[AdminCategoryOut]


class AdminCategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=5000)
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0, le=1_000_000)
    parent_id: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Nom bo‘sh bo‘lmasligi kerak.")
        return text

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str) -> str:
        return _clean_slug(value, limit=80)

    @field_validator("description")
    @classmethod
    def _description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class AdminCategoryPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=160)
    slug: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=1_000_000)
    parent_id: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("Nom bo‘sh bo‘lmasligi kerak.")
        return text

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_slug(value, limit=80)

    @field_validator("description")
    @classmethod
    def _description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class AdminProductOut(BaseModel):
    id: int
    category_id: int
    name: str
    slug: str
    description: str | None
    sku: str | None
    images: list[str]
    product_type: StoreProductType
    unit: StoreUnit
    dimensions: str | None
    is_active: bool
    is_featured: bool
    sort_order: int
    selling_price: str | None = None
    available_quantity: int | None = None


class AdminProductPage(BaseModel):
    items: list[AdminProductOut]
    page: int
    page_size: int
    total: int


class AdminProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    sku: str | None = Field(default=None, max_length=64)
    category_id: int = Field(ge=1)
    dimensions: str | None = Field(default=None, max_length=160)
    product_type: StoreProductType
    unit: StoreUnit
    is_active: bool = True
    is_featured: bool = False
    sort_order: int = Field(default=0, ge=0, le=1_000_000)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Nom bo‘sh bo‘lmasligi kerak.")
        return text

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str) -> str:
        return _clean_slug(value, limit=120)

    @field_validator("description", "dimensions")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    @field_validator("sku")
    @classmethod
    def _sku(cls, value: str | None) -> str | None:
        return _clean_sku(value)


class AdminStockPatch(BaseModel):
    """Tayyor mahsulot qoldig‘i. Narx va faollik bu yerda yo‘q."""

    model_config = ConfigDict(extra="forbid")

    available_quantity: int = Field(ge=0, le=1_000_000)


class AdminImageDelete(BaseModel):
    """O‘chiriladigan rasmning saqlangan manzili."""

    model_config = ConfigDict(extra="forbid")

    image: str = Field(min_length=1, max_length=500)

    @field_validator("image")
    @classmethod
    def _image(cls, value: str) -> str:
        text = value.strip()
        if not text or ".." in text or "\\" in text or not text.startswith("/media/"):
            raise ValueError("Rasm manzili noto‘g‘ri.")
        return text


class AdminProductPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    sku: str | None = Field(default=None, max_length=64)
    category_id: int | None = Field(default=None, ge=1)
    dimensions: str | None = Field(default=None, max_length=160)
    is_active: bool | None = None
    is_featured: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=1_000_000)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("Nom bo‘sh bo‘lmasligi kerak.")
        return text

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_slug(value, limit=120)

    @field_validator("description", "dimensions")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    @field_validator("sku")
    @classmethod
    def _sku(cls, value: str | None) -> str | None:
        return _clean_sku(value)
