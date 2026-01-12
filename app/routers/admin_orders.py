# app/routers/admin_orders.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.order import OrderDetailResponse, OrderListResponse, OrderListItem, OrderStatusUpdate
from app.crud.order import get_all_orders, count_orders, get_order_by_id, update_order_status, delete_order
from app.models.order import OrderStatus
from app.auth.jwt import get_current_admin_user
from app.models.user import User

router = APIRouter()


@router.get("/orders/{order_id}")
async def admin_get_order(
        order_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_admin_user)
):
    """Получить детальную информацию о заказе (только для администраторов)"""

    print(f"🔍 Admin fetching order details for ID: {order_id}")

    try:
        order = get_order_by_id(db, order_id)
        if not order:
            print(f"❌ Order {order_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Заказ не найден"
            )

        # Формируем список товаров
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

        # Формируем ответ
        result = {
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

        print(f"✅ Order details found: {order.order_number}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching order {order_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка сервера: {str(e)}"
        )


@router.get("/orders")
async def admin_get_orders(
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        status: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_admin_user)
):
    """Получить список всех заказов (только для администраторов)"""

    print(f"🔍 Admin fetching orders: page={page}, limit={limit}, status={status}")

    # Преобразуем строку статуса в enum если указан
    order_status = None
    if status:
        try:
            order_status = OrderStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неверный статус: {status}"
            )

    # Получаем заказы
    skip = (page - 1) * limit
    orders = get_all_orders(db, skip=skip, limit=limit, status=order_status)
    total_count = count_orders(db, status=order_status)

    print(f"📊 Found {len(orders)} orders, total: {total_count}")

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


@router.patch("/orders/{order_id}/status")
async def admin_update_order_status(
        order_id: int,
        status_data: dict,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_admin_user)
):
    """Обновить статус заказа (только для администраторов)"""

    try:
        print(f"🔄 Admin updating order {order_id} status to: {status_data}")

        # Получаем заказ
        order = get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Заказ не найден"
            )

        # Получаем новый статус из данных
        new_status_str = status_data.get("status")
        if not new_status_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Статус не указан"
            )

        # Преобразуем строку в enum
        try:
            new_status = OrderStatus(new_status_str)
        except ValueError:
            valid_statuses = [s.value for s in OrderStatus]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неверный статус. Допустимые значения: {valid_statuses}"
            )

        # Обновляем статус
        updated_order = update_order_status(db, order_id, new_status)

        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось обновить статус"
            )

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении статуса: {str(e)}"
        )


@router.put("/orders/{order_id}/status")
async def admin_update_order_status_put(
        order_id: int,
        status_data: dict,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_admin_user)
):
    """Обновить статус заказа PUT метод (для совместимости)"""
    return await admin_update_order_status(order_id, status_data, db, current_user)


@router.delete("/orders/{order_id}")
async def admin_delete_order(
        order_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_admin_user)
):
    """Удалить заказ (только для администраторов)"""

    print(f"🗑️ Admin deleting order {order_id}")

    success = delete_order(db, order_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден"
        )

    print(f"✅ Order {order_id} deleted")
    return {"message": "Заказ успешно удален"}