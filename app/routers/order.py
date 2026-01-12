# app/routers/order.py
from fastapi import APIRouter, Depends, HTTPException, Cookie, Request, Response, status, Header
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.schemas.order import OrderCreate, OrderDetailResponse, OrderListResponse, OrderListItem
from app.crud.order import (
    create_order,
    get_user_orders,
    get_order_by_number,
    get_user_orders_by_id,
    get_order_by_id,
    update_order_status
)
from app.routers.cart import get_user_session
from app.auth.jwt import get_current_user, get_current_active_user, get_current_admin_user
from app.models.order import OrderStatus
from app.models.user import User
import datetime

router = APIRouter()


def get_user_from_token(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Optional[User]:
    """Получить пользователя из токена (опционально)"""
    if not authorization:
        return None

    try:
        # Проверяем формат заголовка
        if not authorization.startswith("Bearer "):
            return None

        token = authorization.split(" ")[1]

        from jose import jwt
        from app.config import settings

        # Декодируем токен
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")

        if not email:
            return None

        # Получаем пользователя из БД
        user = db.query(User).filter(User.email == email).first()
        return user

    except Exception as e:
        print(f"Failed to get user from token: {e}")
        return None


@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_new_order(
        order_data: OrderCreate,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None),
        x_user_session: Optional[str] = Header(None, alias="X-User-Session"),
        current_user: Optional[User] = Depends(get_user_from_token)
):
    """Создать новый заказ из товаров в корзине"""
    try:
        print("=" * 50)
        print("🔍 CREATING ORDER - START")
        print(f"🔍 Session from cookie: {session}")
        print(f"🔍 Session from header: {x_user_session}")

        # Use session from header first (from frontend), then cookie
        user_session = x_user_session or get_user_session(request, response, session)
        print(f"🔍 Final user session: {user_session}")

        # Check cart items for this session
        from app.models.cart import CartItem
        cart_items = db.query(CartItem).filter(CartItem.user_session == user_session).all()
        print(f"🔍 Found {len(cart_items)} items in cart for session {user_session}")

        # If no items found, let's debug further
        if not cart_items:
            print("🔍 No cart items found, checking all sessions...")
            all_cart_items = db.query(CartItem).all()
            for item in all_cart_items:
                print(f"🔍 Cart item session: {item.user_session}")

        user_id = current_user.id if current_user else None
        if user_id:
            print(f"🔍 Authorized user ID: {user_id}")

        order = create_order(
            db=db,
            user_session=user_session,
            customer_name=order_data.customer_name,
            contact_phone=order_data.contact_phone,
            contact_email=order_data.contact_email,
            notes=order_data.notes,
            user_id=user_id
        )

        print(f"✅ Order created: {order.order_number}")

        # Преобразуем данные для ответа
        order_items = []
        for item in order.items:
            order_items.append({
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else "Неизвестный товар",
                "quantity": item.quantity,
                "price": float(item.price),
                "comment": item.comment
            })

        result = {
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status.value if hasattr(order.status, 'value') else order.status,
            "total_amount": float(order.total_amount),
            "customer_name": order.customer_name,
            "contact_phone": order.contact_phone,
            "contact_email": order.contact_email,
            "notes": order.notes,
            "items": order_items,
            "created_at": order.created_at.isoformat() if order.created_at else None
        }

        print("=" * 50)
        return result

    except ValueError as e:
        print(f"❌ ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка при создании заказа: {str(e)}")


@router.get("/orders")
async def get_orders_list(
        request: Request,
        response: Response,
        page: int = 1,
        limit: int = 10,
        search_date: Optional[str] = None,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None),
        current_user: Optional[User] = Depends(get_user_from_token)
):
    """Получить список заказов пользователя"""

    print(f"Getting orders - User: {current_user.id if current_user else 'Anonymous'}, Page: {page}, Limit: {limit}")

    # Получаем заказы в зависимости от авторизации
    if current_user:
        # Если пользователь авторизован, получаем заказы по user_id
        orders = get_user_orders_by_id(db, current_user.id)
        print(f"Found {len(orders)} orders for user_id: {current_user.id}")
    else:
        # Иначе по сессии
        user_session = get_user_session(request, response, session)
        orders = get_user_orders(db, user_session)
        print(f"Found {len(orders)} orders for session: {user_session}")

    # Фильтрация по дате, если указана
    if search_date:
        try:
            search_date_obj = datetime.datetime.strptime(search_date, "%d.%m.%Y")
            filtered_orders = []
            for order in orders:
                if order.created_at.date() == search_date_obj.date():
                    filtered_orders.append(order)
            orders = filtered_orders
            print(f"Filtered to {len(orders)} orders for date: {search_date}")
        except ValueError:
            pass

    # Подсчет общего количества
    total_count = len(orders)

    # Пагинация
    start = (page - 1) * limit
    end = start + limit
    paginated_orders = orders[start:end]

    # Формируем ответ
    order_items = []
    for order in paginated_orders:
        items_count = sum(item.quantity for item in order.items)
        order_items.append({
            "id": order.id,
            "order_number": order.order_number,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "status": order.status.value if hasattr(order.status, 'value') else order.status,
            "items_count": items_count,
            "total_amount": float(order.total_amount),
            "customer_name": order.customer_name,
            "contact_phone": order.contact_phone,
            "contact_email": order.contact_email
        })

    result = {
        "items": order_items,
        "total": total_count,
        "page": page,
        "limit": limit
    }

    print(f"Returning {len(order_items)} orders")
    return result


@router.get("/orders/{order_id}")
async def get_order_details(
        order_id: str,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None),
        current_user: Optional[User] = Depends(get_user_from_token)
):
    """Получить детальную информацию о заказе"""

    print(f"Getting order details for: {order_id}")

    # Сначала пробуем найти по номеру заказа
    if current_user:
        order = get_order_by_number(db, order_id, user_id=current_user.id)
    else:
        user_session = get_user_session(request, response, session)
        order = get_order_by_number(db, order_id, user_session=user_session)

    # Если не нашли по номеру, пробуем по ID
    if not order:
        try:
            order_id_int = int(order_id)
            order = get_order_by_id(db, order_id_int)

            # Проверяем доступ к заказу
            if order:
                if current_user:
                    if order.user_id != current_user.id:
                        order = None
                else:
                    user_session = get_user_session(request, response, session)
                    if order.user_session != user_session:
                        order = None
        except ValueError:
            pass

    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    # Преобразуем данные
    order_items = []
    for item in order.items:
        order_items.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product.name if item.product else "Неизвестный товар",
            "quantity": item.quantity,
            "price": float(item.price),
            "comment": item.comment
        })

    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status.value if hasattr(order.status, 'value') else order.status,
        "total_amount": float(order.total_amount),
        "customer_name": order.customer_name,
        "contact_phone": order.contact_phone,
        "contact_email": order.contact_email,
        "notes": order.notes,
        "items": order_items,
        "created_at": order.created_at.isoformat() if order.created_at else None
    }


@router.put("/orders/{order_id}/cancel")
async def cancel_order(
        order_id: int,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None),
        current_user: Optional[User] = Depends(get_user_from_token)
):
    """Отменить заказ"""

    # Получаем заказ
    order = get_order_by_id(db, order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    # Проверяем доступ к заказу
    if current_user:
        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Нет доступа к этому заказу")
    else:
        user_session = get_user_session(request, response, session)
        if order.user_session != user_session:
            raise HTTPException(status_code=403, detail="Нет доступа к этому заказу")

    # Проверяем, можно ли отменить заказ
    if order.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
        raise HTTPException(
            status_code=400,
            detail=f"Заказ со статусом '{order.status.value}' не может быть отменен"
        )

    # Отменяем заказ
    updated_order = update_order_status(db, order_id, OrderStatus.CANCELLED)

    return {
        "id": updated_order.id,
        "order_number": updated_order.order_number,
        "status": updated_order.status.value,
        "message": "Заказ успешно отменен"
    }


# ============================================
# АДМИНИСТРАТИВНЫЕ ЭНДПОИНТЫ
# ============================================

@router.get("/admin/orders", dependencies=[Depends(get_current_admin_user)])
async def get_all_orders_admin(
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """Получить все заказы (только для администраторов)"""

    from app.crud.order import get_all_orders, count_orders

    # Преобразуем строку статуса в enum если указан
    order_status = None
    if status:
        try:
            order_status = OrderStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Неверный статус: {status}")

    # Получаем заказы
    skip = (page - 1) * limit
    orders = get_all_orders(db, skip=skip, limit=limit, status=order_status)
    total_count = count_orders(db, status=order_status)

    # Формируем ответ
    order_items = []
    for order in orders:
        items_count = sum(item.quantity for item in order.items)
        order_items.append({
            "id": order.id,
            "order_number": order.order_number,
            "user_id": order.user_id,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "status": order.status.value if hasattr(order.status, 'value') else order.status,
            "items_count": items_count,
            "total_amount": float(order.total_amount),
            "customer_name": order.customer_name,
            "contact_phone": order.contact_phone,
            "contact_email": order.contact_email
        })

    return {
        "items": order_items,
        "total": total_count,
        "page": page,
        "limit": limit
    }


@router.get("/admin/orders/{order_id}", dependencies=[Depends(get_current_admin_user)])
async def get_order_details_admin(
        order_id: int,
        db: Session = Depends(get_db)
):
    """Получить детали заказа (только для администраторов)"""

    order = get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    # Формируем ответ
    order_items = []
    for item in order.items:
        order_items.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product.name if item.product else "Неизвестный товар",
            "quantity": item.quantity,
            "price": float(item.price),
            "comment": item.comment
        })

    return {
        "id": order.id,
        "order_number": order.order_number,
        "user_id": order.user_id,
        "status": order.status.value if hasattr(order.status, 'value') else order.status,
        "total_amount": float(order.total_amount),
        "customer_name": order.customer_name,
        "contact_phone": order.contact_phone,
        "contact_email": order.contact_email,
        "notes": order.notes,
        "items": order_items,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None
    }


@router.patch("/admin/orders/{order_id}/status", dependencies=[Depends(get_current_admin_user)])
async def update_order_status_admin(
        order_id: int,
        status_data: dict,
        db: Session = Depends(get_db)
):
    """Обновить статус заказа (только для администраторов)"""

    try:
        print(f"🔍 Updating order {order_id} status to: {status_data}")

        # Получаем заказ
        order = get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")

        # Получаем новый статус из данных
        new_status_str = status_data.get("status")
        if not new_status_str:
            raise HTTPException(status_code=400, detail="Статус не указан")

        # Преобразуем строку в enum
        try:
            new_status = OrderStatus(new_status_str)
        except ValueError:
            valid_statuses = [s.value for s in OrderStatus]
            raise HTTPException(
                status_code=400,
                detail=f"Неверный статус. Допустимые значения: {valid_statuses}"
            )

        # Обновляем статус
        updated_order = update_order_status(db, order_id, new_status)

        if not updated_order:
            raise HTTPException(status_code=500, detail="Не удалось обновить статус")

        print(f"✅ Order {order_id} status updated to: {new_status.value}")

        return {
            "success": True,
            "message": "Статус успешно обновлен",
            "order_id": updated_order.id,
            "order_number": updated_order.order_number,
            "status": updated_order.status.value
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating order status: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении статуса: {str(e)}")


@router.delete("/admin/orders/{order_id}", dependencies=[Depends(get_current_admin_user)])
async def delete_order_admin(
        order_id: int,
        db: Session = Depends(get_db)
):
    """Удалить заказ (только для администраторов)"""

    from app.crud.order import delete_order

    success = delete_order(db, order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    return {
        "success": True,
        "message": "Заказ успешно удален",
        "order_id": order_id
    }