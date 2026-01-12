from sqlalchemy.orm import Session
from app.models.currency import CurrencyRate


def get_active_currency_rate(db: Session, currency_code: str):
    return db.query(CurrencyRate).filter(
        CurrencyRate.currency_code == currency_code,
        CurrencyRate.is_active == True
    ).first()


def create_currency_rate(db: Session, currency_code: str, rate: float, admin_id: int):
    # Деактивируем старый курс
    db.query(CurrencyRate).filter(
        CurrencyRate.currency_code == currency_code
    ).update({"is_active": False})

    # Создаем новый
    db_rate = CurrencyRate(
        currency_code=currency_code,
        rate_to_rub=rate,
        created_by=admin_id
    )
    db.add(db_rate)
    db.commit()
    db.refresh(db_rate)
    return db_rate


def get_all_active_rates(db: Session):
    return db.query(CurrencyRate).filter(CurrencyRate.is_active == True).all()