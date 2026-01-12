# app/routers/admin_currency.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.currency import CurrencyRateCreate, CurrencyRateResponse
from app.crud.currency import create_currency_rate, get_all_active_rates
from app.auth.jwt import get_current_admin_user
from app.models.user import User

router = APIRouter()

@router.post("/currency-rates", response_model=CurrencyRateResponse)
async def set_currency_rate(
    rate_data: CurrencyRateCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Установка нового курса валюты"""
    return create_currency_rate(
        db,
        rate_data.currency_code,
        rate_data.rate_to_rub,
        current_admin.id  # ID администратора берется из токена
    )

@router.get("/currency-rates")
async def get_currency_rates(db: Session = Depends(get_db)):
    """Получение всех активных курсов валют"""
    return get_all_active_rates(db)