from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ProductBase(BaseModel):
    """Базовая схема для товара"""
    name: str
    description: Optional[str] = None
    brand: Optional[str] = None
    volume: Optional[str] = None


class ProductCreate(ProductBase):
    """Схема для создания товара"""
    price_rub: float = Field(..., gt=0)


class ProductUpdate(BaseModel):
    """
    Схема для обновления товара.

    Все поля опциональные, чтобы можно было обновлять только нужные поля.
    """
    name: Optional[str] = None
    price_rub: Optional[float] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    volume: Optional[str] = None


class ProductDetail(BaseModel):
    """Схема для детального представления товара"""
    id: int
    name: str
    price: float
    price_formatted: str
    currency: str
    description: Optional[str] = None
    brand: Optional[str] = None
    volume: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ProductListItem(BaseModel):
    """Схема для элемента в списке товаров"""
    id: int
    name: str
    price: float
    price_formatted: str
    currency: str
    updated_date: str
    default_quantity: int = 1
    brand: Optional[str] = None
    volume: Optional[str] = None

    class Config:
        orm_mode = True


class ProductListResponse(BaseModel):
    """Схема для ответа со списком товаров"""
    products: List[ProductListItem]
    total_count: int
    current_page: int
    per_page: int
    has_next: bool
    has_prev: bool
