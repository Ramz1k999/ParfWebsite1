from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class CurrencyRate(Base):
    __tablename__ = "currency_rates"

    id = Column(Integer, primary_key=True, index=True)
    currency_code = Column(String(3), nullable=False, index=True)  # RUB, EUR
    rate_to_usd = Column(Numeric(12, 6), nullable=False)  # Курс к доллару
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer)  # ID администратора
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
