from fastapi import APIRouter, Depends, HTTPException, Cookie, Request, status, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.schemas.cart import CartAddRequest, CartRemoveRequest, CartResponse, CartItemResponse, CartCommentRequest, \
    CartCheckoutPreview
from app.crud.cart import add_to_cart, remove_from_cart, get_cart_items, clear_cart, update_cart_quantity, \
    update_cart_comment, get_cart_item_by_id
from app.crud.product import convert_price, get_product_by_id
import uuid

router = APIRouter()


def get_user_session(request: Request, response: Response, session: Optional[str] = Cookie(None)):
    """Получить или создать идентификатор сессии пользователя"""
    # Сначала проверяем заголовок
    header_session = request.headers.get('X-User-Session')
    if header_session:
        print(f"Using session from header: {header_session}")
        return header_session

    # Затем проверяем куку
    if session:
        print(f"Using session from cookie: {session}")
        return session

    # Если ни того, ни другого нет, создаем новую сессию
    new_session = str(uuid.uuid4())
    print(f"Creating new session: {new_session}")

    # Устанавливаем куку на 30 дней
    response.set_cookie(
        key="session",
        value=new_session,
        max_age=60 * 60 * 24 * 30,  # 30 дней
        httponly=True,
        samesite="lax",  # Важно для работы с современными браузерами
        secure=False  # Для разработки, в продакшене установите True
    )
    return new_session


@router.post("/cart/add")
async def add_item_to_cart(
        item: CartAddRequest,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    """Добавить товар в корзину"""
    user_session = get_user_session(request, response, session)
    print(f"Adding item to cart: id={item.id}, count={item.count}, session={user_session}")

    try:
        cart_item = add_to_cart(db, user_session, item.id, item.count)
        print(f"Item added successfully: {cart_item.id}")

        # Возвращаем JSONResponse с куками
        content = {"success": True, "message": "Товар добавлен в корзину"}
        return JSONResponse(content=content)
    except ValueError as e:
        print(f"Error adding item to cart: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/cart/comment")
async def add_comment_to_cart_item(
        comment_data: CartCommentRequest,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    """Добавить или обновить комментарий к товару в корзине"""
    user_session = get_user_session(request, response, session)
    print(f"Adding comment to cart item: id={comment_data.id}, session={user_session}")

    # Проверяем, что товар принадлежит этому пользователю
    cart_item = get_cart_item_by_id(db, comment_data.id)
    if not cart_item or cart_item.user_session != user_session:
        print(f"Item not found in cart or belongs to another session")
        raise HTTPException(status_code=404, detail="Товар не найден в корзине")

    updated_item = update_cart_comment(db, comment_data.id, comment_data.comment)
    if updated_item:
        print(f"Comment added successfully")
        return JSONResponse(content={"success": True, "message": "Комментарий добавлен"})

    print(f"Failed to update comment")
    raise HTTPException(status_code=404, detail="Не удалось обновить комментарий")


@router.post("/cart/remove")
async def remove_item_from_cart(
        item: CartRemoveRequest,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    """Удалить товар из корзины"""
    user_session = get_user_session(request, response, session)
    print(f"Removing item from cart: id={item.id}, session={user_session}")

    # 🔥 ИСПРАВЛЕНО: удаляем по ID записи корзины, а не по product_id
    cart_item = get_cart_item_by_id(db, item.id)
    if cart_item and cart_item.user_session == user_session:
        db.delete(cart_item)
        db.commit()
        print(f"Item removed successfully")
        return JSONResponse(content={"success": True, "message": "Товар удален из корзины"})

    print(f"Item not found in cart")
    raise HTTPException(status_code=404, detail="Товар не найден в корзине")


@router.get("/cart", response_model=CartResponse)
async def get_cart(
        request: Request,
        response: Response,
        currency: str = "RUB",
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    """Получить содержимое корзины"""
    user_session = get_user_session(request, response, session)
    print(f"Getting cart contents for session: {user_session}")

    cart_items = get_cart_items(db, user_session)
    print(f"Found {len(cart_items)} items in cart")

    items_response = []
    total_items = 0
    total_price_value = 0

    currency_symbol = "руб." if currency == "RUB" else "$"

    for item in cart_items:
        product = get_product_by_id(db, item.product_id)
        if product:
            # Конвертируем цену в нужную валюту
            price_per_item = convert_price(db, float(product.price_rub), currency)
            item_total = price_per_item * item.quantity

            # Форматируем цены для отображения
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
                    price=price_per_item,  # 🔥 Число
                    price_formatted=price_formatted,  # 🔥 Строка для отображения
                    total_price=item_total,  # 🔥 Число
                    total_price_formatted=total_formatted  # 🔥 Строка для отображения
                )
            )

            total_items += item.quantity
            total_price_value += item_total

    total_price_formatted = f"{total_price_value:.1f} {currency_symbol}".replace(".", ",")

    print(f"Total items: {total_items}, Total price: {total_price_formatted}")

    return CartResponse(
        items=items_response,
        total_items=total_items,
        total_price=total_price_formatted
    )


@router.post("/cart/update")
async def update_item_quantity(
        item: CartAddRequest,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    """Обновить количество товара в корзине"""
    user_session = get_user_session(request, response, session)
    print(f"Updating item quantity in cart: id={item.id}, count={item.count}, session={user_session}")

    # 🔥 ИСПРАВЛЕНО: работаем с ID записи корзины
    cart_item = get_cart_item_by_id(db, item.id)

    if not cart_item or cart_item.user_session != user_session:
        print(f"Item not found in cart or belongs to another session")
        raise HTTPException(status_code=404, detail="Товар не найден в корзине")

    # Если количество 0, удаляем товар из корзины
    if item.count == 0:
        db.delete(cart_item)
        db.commit()
        print(f"Item removed due to zero quantity")
        return JSONResponse(content={"success": True, "message": "Товар удален из корзины"})

    # Иначе обновляем количество
    cart_item.quantity = item.count
    db.commit()
    db.refresh(cart_item)
    print(f"Item quantity updated successfully")
    return JSONResponse(content={"success": True, "message": "Количество товара обновлено"})


@router.get("/cart/checkout-preview", response_model=CartCheckoutPreview)
async def checkout_preview(
        request: Request,
        response: Response,
        currency: str = "RUB",
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    """Предварительный просмотр заказа перед оформлением"""
    print(f"Getting checkout preview")

    # Используем ту же логику, что и в get_cart
    cart_response = await get_cart(request, response, currency, db, session)

    # Добавляем заглушку для контактной информации
    # В реальном приложении здесь можно получать сохраненную информацию пользователя
    return CartCheckoutPreview(
        items=cart_response.items,
        total_items=cart_response.total_items,
        total_price=cart_response.total_price,
        contact_info=None  # Здесь можно вернуть сохраненную контактную информацию
    )


@router.get("/cart/print")
async def print_cart(
        request: Request,
        response: Response,
        currency: str = "RUB",
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    """Получить корзину в формате для печати"""
    print(f"Getting cart for printing")

    # Здесь можно добавить логику для генерации PDF или другого формата для печати
    # В простейшем случае возвращаем тот же ответ, что и для обычного получения корзины
    return await get_cart(request, response, currency, db, session)


@router.post("/cart/clear")
async def clear_user_cart(
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        session: Optional[str] = Cookie(None)
):
    """Очистить корзину пользователя"""
    user_session = get_user_session(request, response, session)
    print(f"Clearing cart for session: {user_session}")

    clear_cart(db, user_session)
    return JSONResponse(content={"success": True, "message": "Корзина очищена"})