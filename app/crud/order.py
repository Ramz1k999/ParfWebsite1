# app/crud/order.py
from sqlalchemy.orm import Session
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.cart import CartItem
from typing import Optional
import random
import string


def generate_order_number():
    """Генерация уникального 6-значного номера заказа"""
    return ''.join(random.choices(string.digits, k=6))


def create_order(
        db: Session,
        user_session: str,
        customer_name: str,
        contact_phone: str,
        contact_email: str,
        notes: Optional[str] = None,
        user_id: Optional[int] = None
) -> Order:
    """
    Создание нового заказа из товаров в корзине.

    Args:
        db: сессия базы данных
        user_session: идентификатор сессии пользователя
        customer_name: имя клиента
        contact_phone: контактный телефон
        contact_email: контактный email
        notes: дополнительные примечания
        user_id: ID пользователя (если авторизован)

    Returns:
        Order: созданный заказ

    Raises:
        ValueError: если корзина пуста
    """

    # Получаем все товары из корзины
    cart_items = db.query(CartItem).filter(CartItem.user_session == user_session).all()
    if not cart_items:
        raise ValueError("Корзина пуста")

    # Генерируем уникальный номер заказа
    order_number = generate_order_number()
    while db.query(Order).filter(Order.order_number == order_number).first():
        order_number = generate_order_number()

    # Вычисляем общую сумму заказа
    total_amount = 0
    for item in cart_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            total_amount += float(product.price_rub) * item.quantity

    # Создаем объект заказа с правильным статусом на русском
    new_order = Order(
        order_number=order_number,
        user_session=user_session,
        user_id=user_id,
        status=OrderStatus.PENDING.value,  # 🔥 статус теперь корректный для базы
        total_amount=total_amount,
        customer_name=customer_name,
        contact_phone=contact_phone,
        contact_email=contact_email,
        notes=notes
    )

    db.add(new_order)
    db.flush()  # Получаем ID заказа

    # Добавляем товары из корзины в заказ
    for item in cart_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=float(product.price_rub),
                comment=item.comment
            )
            db.add(order_item)

    # Очищаем корзину
    db.query(CartItem).filter(CartItem.user_session == user_session).delete()

    db.commit()
    db.refresh(new_order)
    return new_order



def get_user_orders(db: Session, user_session: str) -> List[Order]:
    """
    Получить все заказы пользователя по сессии.

    Args:
        db: Сессия базы данных
        user_session: Идентификатор сессии пользователя

    Returns:
        List[Order]: Список заказов пользователя
    """
    return db.query(Order).filter(Order.user_session == user_session).order_by(desc(Order.created_at)).all()


def get_user_orders_by_id(db: Session, user_id: int) -> List[Order]:
    """
    Получить все заказы пользователя по ID.

    Args:
        db: Сессия базы данных
        user_id: ID пользователя

    Returns:
        List[Order]: Список заказов пользователя
    """
    return db.query(Order).filter(Order.user_id == user_id).order_by(desc(Order.created_at)).all()


def get_order_by_number(db: Session, order_number: str, user_session: str = None, user_id: int = None) -> Optional[Order]:
    """
    Получить заказ по номеру.

    Args:
        db: Сессия базы данных
        order_number: Номер заказа
        user_session: Идентификатор сессии пользователя (опционально)
        user_id: ID пользователя (опционально)

    Returns:
        Optional[Order]: Заказ или None, если заказ не найден
    """
    query = db.query(Order).filter(Order.order_number == order_number)

    # Если указан user_session или user_id, добавляем фильтр
    if user_session:
        query = query.filter(Order.user_session == user_session)
    if user_id:
        query = query.filter(Order.user_id == user_id)

    return query.first()


def get_order_by_id(db: Session, order_id: int) -> Optional[Order]:
    """
    Получить заказ по ID.

    Args:
        db: Сессия базы данных
        order_id: ID заказа

    Returns:
        Optional[Order]: Заказ или None, если заказ не найден
    """
    return db.query(Order).filter(Order.id == order_id).first()


def update_order_status(db: Session, order_id: int, status: OrderStatus) -> Optional[Order]:
    """
    Обновить статус заказа.

    Args:
        db: Сессия базы данных
        order_id: ID заказа
        status: Новый статус заказа

    Returns:
        Optional[Order]: Обновленный заказ или None, если заказ не найден
    """
    order = get_order_by_id(db, order_id)
    if not order:
        return None

    order.status = status
    db.commit()
    db.refresh(order)
    return order


def get_order_items(db: Session, order_id: int) -> List[OrderItem]:
    """
    Получить все товары в заказе.

    Args:
        db: Сессия базы данных
        order_id: ID заказа

    Returns:
        List[OrderItem]: Список товаров в заказе
    """
    return db.query(OrderItem).filter(OrderItem.order_id == order_id).all()


def get_order_items_count(db: Session, order_id: int) -> int:
    """
    Получить количество товаров в заказе.

    Args:
        db: Сессия базы данных
        order_id: ID заказа

    Returns:
        int: Количество товаров в заказе
    """
    items = get_order_items(db, order_id)
    return sum(item.quantity for item in items)


def get_all_orders(db: Session, skip: int = 0, limit: int = 100, status: Optional[OrderStatus] = None) -> List[Order]:
    """
    Получить все заказы с возможностью фильтрации по статусу.

    Args:
        db: Сессия базы данных
        skip: Сколько записей пропустить
        limit: Максимальное количество записей
        status: Статус для фильтрации (опционально)

    Returns:
        List[Order]: Список заказов
    """
    query = db.query(Order)

    if status:
        query = query.filter(Order.status == status)

    return query.order_by(desc(Order.created_at)).offset(skip).limit(limit).all()


def count_orders(db: Session, status: Optional[OrderStatus] = None) -> int:
    """
    Получить общее количество заказов с возможностью фильтрации по статусу.

    Args:
        db: Сессия базы данных
        status: Статус для фильтрации (опционально)

    Returns:
        int: Количество заказов
    """
    query = db.query(Order)

    if status:
        query = query.filter(Order.status == status)

    return query.count()


def delete_order(db: Session, order_id: int) -> bool:
    """
    Удалить заказ.

    Args:
        db: Сессия базы данных
        order_id: ID заказа

    Returns:
        bool: True если заказ удален, иначе False
    """
    order = get_order_by_id(db, order_id)
    if not order:
        return False

    db.delete(order)
    db.commit()
    return True
