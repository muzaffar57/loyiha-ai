from pydantic import BaseModel, Field


class StoreAdminLogin(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class StoreAdminToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StoreAdminOut(BaseModel):
    id: int
    full_name: str
    email: str
    is_active: bool
