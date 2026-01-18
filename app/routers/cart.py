# app/routers/cart.py
from fastapi import APIRouter, Depends, HTTPException, Cookie, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas.cart import (
    CartAddRequest,
    CartRemoveRequest,
    CartResponse,
    CartItemResponse,
    CartCommentRequest,
    CartCheckoutPreview,
)
from app.crud.cart import (
    add_to_cart,
    remove_from_cart,
    get_cart_items,
    clear_cart,
    update_cart_quantity,
    update_cart_comment,
    get_cart_item_by_id,
)
from app.crud.product import convert_price, get_product_by_id
import uuid

router = APIRouter()


def get_user_session(request: Request, response: Response, session: Optional[str] = Cookie(None)):
    """Получить или создать идентификатор сессии пользователя"""
    header_session = request.headers.get("X-User-Session")
    if header_session:
        return header_session

    if session:
        return session

    # Создаем новую сессию
    new_session = str(uuid.uuid4())
    response.set_cookie(
        key="session",
        value=new_session,
        max_age=60 * 60 * 24 * 30,  # 30 дней
        httponly=True,
        samesite="lax",
        secure=False  # Для продакшена True
    )
    return new_session


# --- CORS preflight handler ---
@router.options("/{full_path:path}")
async def preflight_handler():
    """Пропускаем все preflight OPTIONS запросы для CORS"""
    return JSONResponse(content={}, status_code=200)


# --- Добавление товара ---
@router.post("/cart/add")
async def add_item_to_cart(
        item: CartAddRequest,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    user_session = get_user_session(request, response, session)
    try:
        cart_item = add_to_cart(db, user_session, item.id, item.count)
        return JSONResponse(content={"success": True, "message": "Товар добавлен в корзину"})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Добавление комментария ---
@router.post("/cart/comment")
async def add_comment_to_cart_item(
        comment_data: CartCommentRequest,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    user_session = get_user_session(request, response, session)
    cart_item = get_cart_item_by_id(db, comment_data.id)
    if not cart_item or cart_item.user_session != user_session:
        raise HTTPException(status_code=404, detail="Товар не найден в корзине")

    updated_item = update_cart_comment(db, comment_data.id, comment_data.comment)
    if updated_item:
        return JSONResponse(content={"success": True, "message": "Комментарий добавлен"})
    raise HTTPException(status_code=404, detail="Не удалось обновить комментарий")


# --- Удаление товара ---
@router.post("/cart/remove")
async def remove_item_from_cart(
        item: CartRemoveRequest,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    user_session = get_user_session(request, response, session)
    cart_item = get_cart_item_by_id(db, item.id)
    if cart_item and cart_item.user_session == user_session:
        db.delete(cart_item)
        db.commit()
        return JSONResponse(content={"success": True, "message": "Товар удален из корзины"})
    raise HTTPException(status_code=404, detail="Товар не найден в корзине")


# --- Получение корзины ---
@router.get("/cart", response_model=CartResponse)
async def get_cart(
        request: Request,
        response: Response,
        currency: str = "RUB",
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    user_session = get_user_session(request, response, session)
    cart_items = get_cart_items(db, user_session)

    items_response = []
    total_items = 0
    total_price_value = 0
    currency_symbol = "руб." if currency == "RUB" else "$"

    for item in cart_items:
        product = get_product_by_id(db, item.product_id)
        if product:
            price_per_item = convert_price(db, float(product.price_rub), currency)
            item_total = price_per_item * item.quantity

            price_formatted = f"{price_per_item:.1f} {currency_symbol}".replace(".", ",")
            total_formatted = f"{item_total:.1f} {currency_symbol}".replace(".", ",")

            items_response.append(
                CartItemResponse(
                    id=item.id,
                    product_id=item.product_id,
                    product_name=product.name,
                    product_brand=product.brand,
                    product_volume=product.volume,
                    quantity=item.quantity,
                    comment=item.comment,
                    price=price_per_item,
                    price_formatted=price_formatted,
                    total_price=item_total,
                    total_price_formatted=total_formatted
                )
            )
            total_items += item.quantity
            total_price_value += item_total

    total_price_formatted = f"{total_price_value:.1f} {currency_symbol}".replace(".", ",")

    return CartResponse(
        items=items_response,
        total_items=total_items,
        total_price=total_price_formatted
    )


# --- Обновление количества ---
@router.post("/cart/update")
async def update_item_quantity(
        item: CartAddRequest,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    user_session = get_user_session(request, response, session)
    cart_item = get_cart_item_by_id(db, item.id)
    if not cart_item or cart_item.user_session != user_session:
        raise HTTPException(status_code=404, detail="Товар не найден в корзине")

    if item.count == 0:
        db.delete(cart_item)
        db.commit()
        return JSONResponse(content={"success": True, "message": "Товар удален из корзины"})

    cart_item.quantity = item.count
    db.commit()
    db.refresh(cart_item)
    return JSONResponse(content={"success": True, "message": "Количество товара обновлено"})


# --- Предпросмотр оформления ---
@router.get("/cart/checkout-preview", response_model=CartCheckoutPreview)
async def checkout_preview(
        request: Request,
        response: Response,
        currency: str = "RUB",
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    cart_response = await get_cart(request, response, currency, db, session)
    return CartCheckoutPreview(
        items=cart_response.items,
        total_items=cart_response.total_items,
        total_price=cart_response.total_price,
        contact_info=None
    )


# --- Печать корзины ---
@router.get("/cart/print")
async def print_cart(
        request: Request,
        response: Response,
        currency: str = "RUB",
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    return await get_cart(request, response, currency, db, session)


# --- Очистка корзины ---
@router.post("/cart/clear")
async def clear_user_cart(
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    user_session = get_user_session(request, response, session)
    clear_cart(db, user_session)
    return JSONResponse(content={"success": True, "message": "Корзина очищена"})
