from pydantic import BaseModel
from datetime import datetime


class CurrencyRateCreate(BaseModel):
    currency_code: str
    rate_to_rub: float


class CurrencyRateResponse(BaseModel):
    id: int
    currency_code: str
    rate_to_rub: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
