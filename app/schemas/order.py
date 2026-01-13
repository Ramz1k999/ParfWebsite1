# app/schemas/order.py
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "ожидает подтверждения"
    PROCESSING = "в обработке"
    SHIPPED = "отправлен"
    DELIVERED = "доставлен"
    CANCELLED = "отменен"


# Схема для создания заказа
class OrderCreate(BaseModel):
    customer_name: str
    contact_phone: str
    contact_email: EmailStr
    notes: Optional[str] = None


# Схема для элемента заказа в ответе API
class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    price: float
    comment: Optional[str] = None  # Комментарий к товару

    class Config:
        orm_mode = True


# Схема для детального представления заказа
class OrderDetailResponse(BaseModel):
    id: int
    order_number: str
    status: str
    total_amount: float
    customer_name: str
    contact_phone: str
    contact_email: str
    notes: Optional[str] = None
    items: List[OrderItemResponse]
    created_at: datetime

    class Config:
        orm_mode = True


# Схема для элемента в списке заказов
class OrderListItem(BaseModel):
    order_number: str
    created_at: datetime
    status: str
    items_count: int
    id: Optional[int] = None  # Для админского интерфейса
    customer_name: Optional[str] = None  # Для админского интерфейса
    contact_phone: Optional[str] = None  # Для админского интерфейса
    total_amount: Optional[float] = None  # Для админского интерфейса

    class Config:
        orm_mode = True

# Схема для ответа со списком заказов
class OrderListResponse(BaseModel):
    orders: List[OrderListItem]
    total_count: int


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
