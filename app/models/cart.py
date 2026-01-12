# app/models/cart.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_session = Column(String, nullable=False, index=True)  # Сессия пользователя
    quantity = Column(Integer, default=1)
    comment = Column(Text, nullable=True)  # Комментарий к товару в корзине
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Связь с товаром
    product = relationship("Product", backref="cart_items")