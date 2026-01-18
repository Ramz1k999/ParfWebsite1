# app/schemas/cart.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime


class CartAddRequest(BaseModel):
    id: int
    count: int = Field(default=1, ge=1)
    comment: Optional[str] = None



class CartRemoveRequest(BaseModel):
    id: int = Field(..., description="ID товара")


class CartCommentRequest(BaseModel):
    id: int = Field(..., description="ID товара в корзине")
    comment: str = Field(..., description="Комментарий к товару")


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_brand: Optional[str] = None
    product_volume: Optional[str] = None
    quantity: int
    comment: Optional[str] = None
    price: float  # 🔥 ИЗМЕНЕНО: было str, стало float
    price_formatted: str  # 🔥 ДОБАВЛЕНО: для отображения
    total_price: float  # 🔥 ИЗМЕНЕНО: было str, стало float
    total_price_formatted: str  # 🔥 ДОБАВЛЕНО: для отображения

    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    items: List[CartItemResponse]
    total_items: int = Field(..., description="Общее количество товаров")
    total_price: str = Field(..., description="Общая стоимость, например '0,0 руб.'")


class CartCheckoutPreview(BaseModel):
    items: List[CartItemResponse]
    total_items: int
    total_price: str
    contact_info: Optional[dict] = None  # Контактная информация пользователя, если есть
