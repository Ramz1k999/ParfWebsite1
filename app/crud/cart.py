# app/crud/cart.py
from sqlalchemy.orm import Session
from app.models.cart import CartItem
from app.models.product import Product
from typing import List, Optional


def get_cart_items(db: Session, user_session: str) -> List[CartItem]:
    """Получить все товары в корзине пользователя"""
    return db.query(CartItem).filter(CartItem.user_session == user_session).all()


def get_cart_item(db: Session, user_session: str, product_id: int) -> Optional[CartItem]:
    """Получить конкретный товар из корзины пользователя"""
    return db.query(CartItem).filter(
        CartItem.user_session == user_session,
        CartItem.product_id == product_id
    ).first()


def get_cart_item_by_id(db: Session, cart_item_id: int) -> Optional[CartItem]:
    """Получить товар из корзины по ID записи"""
    return db.query(CartItem).filter(CartItem.id == cart_item_id).first()


def add_to_cart(db: Session, user_session: str, product_id: int, quantity: int = 1, comment: str = None) -> CartItem:
    """Добавить товар в корзину"""
    # Проверяем, существует ли товар
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Товар с ID {product_id} не найден")

    # Проверяем, есть ли уже этот товар в корзине
    cart_item = get_cart_item(db, user_session, product_id)

    if cart_item:
        # Если товар уже в корзине, увеличиваем количество
        cart_item.quantity += quantity
        if comment:
            cart_item.comment = comment
        db.commit()
        db.refresh(cart_item)
        return cart_item
    else:
        # Создаем новый элемент корзины
        new_item = CartItem(
            product_id=product_id,
            user_session=user_session,
            quantity=quantity,
            comment=comment
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return new_item


def remove_from_cart(db: Session, user_session: str, product_id: int) -> bool:
    """Удалить товар из корзины"""
    cart_item = get_cart_item(db, user_session, product_id)
    if cart_item:
        db.delete(cart_item)
        db.commit()
        return True
    return False


def update_cart_quantity(db: Session, user_session: str, product_id: int, quantity: int) -> Optional[CartItem]:
    """Обновить количество товара в корзине"""
    cart_item = get_cart_item(db, user_session, product_id)
    if cart_item:
        cart_item.quantity = quantity
        db.commit()
        db.refresh(cart_item)
        return cart_item
    return None


def update_cart_comment(db: Session, cart_item_id: int, comment: str) -> Optional[CartItem]:
    """Обновить комментарий к товару в корзине"""
    cart_item = get_cart_item_by_id(db, cart_item_id)
    if cart_item:
        cart_item.comment = comment
        db.commit()
        db.refresh(cart_item)
        return cart_item
    return None


def clear_cart(db: Session, user_session: str) -> bool:
    """Очистить всю корзину пользователя"""
    db.query(CartItem).filter(CartItem.user_session == user_session).delete()
    db.commit()
    return True