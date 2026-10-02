from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TrimInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    size: Literal["S", "M", "L"]
    components: list[Literal["cornice", "jamb", "sill"]] = Field(max_length=6)
    extra_meters: dict[str, str] = Field(default_factory=dict)
    addons: list[str] = Field(default_factory=list, max_length=20)


class PilasterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width_cm: str = Field(min_length=1, max_length=32)
    thickness_cm: str = Field(min_length=1, max_length=32)
    length_m: str = Field(min_length=1, max_length=32)
    capital: str | None = Field(default=None, max_length=80)
    base: str | None = Field(default=None, max_length=80)


class RoundColumnInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    existing_diameter_cm: str | None = Field(default=None, max_length=32)
    circumference_cm: str | None = Field(default=None, max_length=40)
    final_diameter_cm: str = Field(min_length=1, max_length=32)
    height_m: str = Field(min_length=1, max_length=32)
    coating: bool = False
    capital: str | None = Field(default=None, max_length=80)
    base: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=160)


class CorniceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width_cm: str = Field(min_length=1, max_length=32)
    length_m: str = Field(min_length=1, max_length=32)
    coating: bool = False


class ShohonaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    length_m: str | None = Field(default=None, max_length=32)
    size_note: str | None = Field(default=None, max_length=200)
    coating: bool = False
    model: str | None = Field(default=None, max_length=160)


class PricingCalculateRequest(BaseModel):
    """Mijoz narx yubormaydi. Qo‘shimcha narx maydonlari hisobga olinmaydi."""

    model_config = ConfigDict(extra="ignore")

    product_id: int = Field(ge=1)
    quantity: int = Field(ge=1, le=9999)
    trim: TrimInput | None = None
    pilaster: PilasterInput | None = None
    round_column: RoundColumnInput | None = None
    cornice: CorniceInput | None = None
    shohona: ShohonaInput | None = None


class PricingComponentOut(BaseModel):
    code: str
    label: str
    amount: str | None
    detail: str | None = None


class PricingQuoteOut(BaseModel):
    status: Literal["PRICED", "MANUAL_QUOTE_REQUIRED"]
    currency: Literal["UZS"] = "UZS"
    unit_price: str | None
    subtotal: str | None
    total: str | None
    components: list[PricingComponentOut]
    requires_manual_quote: bool
    warnings: list[str]
    applied: dict[str, str]
