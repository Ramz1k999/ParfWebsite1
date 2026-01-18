from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class OrderStatus(str, enum.Enum):
    PENDING = "ожидает подтверждения"
    PROCESSING = "в обработке"
    SHIPPED = "отправлен"
    DELIVERED = "доставлен"
    CANCELLED = "отменен"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False)
    user_session = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(SQLEnum(OrderStatus), default="ожидает подтверждения")
    total_amount = Column(Float, nullable=False)
    customer_name = Column(String, nullable=False)
    contact_phone = Column(String, nullable=False)
    contact_email = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Связи
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")  # 🔥 ВАЖНО
    user = relationship("User", backref="orders")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    comment = Column(Text, nullable=True)

    # Связи
    order = relationship("Order", back_populates="items")  # 🔥 ВАЖНО
    product = relationship("Product")
