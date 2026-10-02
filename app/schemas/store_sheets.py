from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SyncStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    stale: bool
    currency: str
    global_price_adjustment_percent: str
    last_success_at: datetime | None
    last_attempt_at: datetime | None
    last_error: str | None
    sheet_updated_at: datetime | None


class SyncResultOut(BaseModel):
    status: str
    updated_products: int
