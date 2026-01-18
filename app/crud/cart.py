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


def add_to_cart(db: Session, user_session: str, product_id: int, quantity: int = 1, comment: str = None):
    print(f"[CART-DEBUG] === START === session='{user_session}' product={product_id} qty={quantity}")

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        print("[CART-DEBUG] Товар не найден!")
        raise ValueError("Товар не найден")

    print(f"[CART-DEBUG] Товар найден → {product.name} (id={product.id})")

    existing = get_cart_item(db, user_session, product_id)
    if existing:
        print(f"[CART-DEBUG] Существующая запись найдена, id={existing.id}, было qty={existing.quantity}")
        existing.quantity += quantity
        if comment is not None:
            existing.comment = comment
        item = existing
    else:
        print("[CART-DEBUG] Создаём новую запись")
        item = CartItem(
            product_id=product_id,
            user_session=user_session.strip(),  # ← на всякий случай убираем пробелы
            quantity=quantity,
            comment=comment
        )
        db.add(item)

    try:
        db.flush()  # ← промежуточный flush, чтобы увидеть id до commit
        print(f"[CART-DEBUG] После flush → временный id={item.id if item.id else 'ещё нет'}")
        db.commit()
        print("[CART-DEBUG] commit выполнен успешно")
        db.refresh(item)
        print(f"[CART-DEBUG] После refresh → id={item.id}, qty={item.quantity}, session='{item.user_session}'")
        return item
    except Exception as exc:
        db.rollback()
        print(f"[CART-DEBUG] ОШИБКА commit: {type(exc).__name__} → {str(exc)}")
        raise

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
