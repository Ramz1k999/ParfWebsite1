from fastapi import APIRouter, Depends, HTTPException, Cookie, Request, Response
from sqlalchemy.orm import Session
from typing import Optional
from fastapi.responses import JSONResponse
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
    update_cart_comment,
    get_cart_item_by_id,
)
from app.crud.product import convert_price, get_product_by_id
import uuid

router = APIRouter()

def get_user_session(request: Request, response: Response, session: Optional[str] = Cookie(None)):
    header_session = request.headers.get("X-User-Session")
    
    if header_session:
        print(f"[SESSION-DEBUG] Использован заголовок X-User-Session: {header_session}")
        return header_session
    
    print(f"[SESSION-DEBUG] Заголовок X-User-Session ОТСУТСТВУЕТ!")
    if session:
        print(f"[SESSION-DEBUG] Использована кука session: {session}")
        return session
    
    # В продакшене лучше выбрасывать ошибку, а не создавать новую
    print("[SESSION-DEBUG] НИКАКОЙ сессии нет → создаём новую")
    new_session = str(uuid.uuid4())
    response.set_cookie(key="session", value=new_session, max_age=60*60*24*30, httponly=True, samesite="lax", secure=False)
    return new_session

# --- CRUD эндпоинты (без CORS в каждом) ---

@router.post("/cart/add")
async def add_item_to_cart(item: CartAddRequest, request: Request, response: Response, db: Session = Depends(get_db), session: Optional[str] = Cookie(None)):
    user_session = get_user_session(request, response, session)
    try:
        add_to_cart(db, user_session, item.id, item.count)
        return {"success": True, "message": "Товар добавлен в корзину"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/cart/comment")
async def add_comment_to_cart_item(comment_data: CartCommentRequest, request: Request, response: Response, db: Session = Depends(get_db), session: Optional[str] = Cookie(None)):
    user_session = get_user_session(request, response, session)
    cart_item = get_cart_item_by_id(db, comment_data.id)
    if not cart_item or cart_item.user_session != user_session:
        raise HTTPException(status_code=404, detail="Товар не найден в корзине")
    updated_item = update_cart_comment(db, comment_data.id, comment_data.comment)
    if updated_item:
        return {"success": True, "message": "Комментарий добавлен"}
    raise HTTPException(status_code=404, detail="Не удалось обновить комментарий")

@router.post("/cart/remove")
async def remove_item_from_cart(item: CartRemoveRequest, request: Request, response: Response, db: Session = Depends(get_db), session: Optional[str] = Cookie(None)):
    user_session = get_user_session(request, response, session)
    cart_item = get_cart_item_by_id(db, item.id)
    if cart_item and cart_item.user_session == user_session:
        db.delete(cart_item)
        db.commit()
        return {"success": True, "message": "Товар удален из корзины"}
    raise HTTPException(status_code=404, detail="Товар не найден в корзине")

@router.get("/cart", response_model=CartResponse)
async def get_cart(request: Request, response: Response, currency: str = "RUB", db: Session = Depends(get_db), session: Optional[str] = Cookie(None)):
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
                    price_formatted=f"{price_per_item:.1f} {currency_symbol}".replace(".", ","),
                    total_price=item_total,
                    total_price_formatted=f"{item_total:.1f} {currency_symbol}".replace(".", ",")
                )
            )
            total_items += item.quantity
            total_price_value += item_total

    return CartResponse(items=items_response, total_items=total_items, total_price=f"{total_price_value:.1f} {currency_symbol}".replace(".", ","))

@router.post("/cart/clear")
async def clear_user_cart(request: Request, response: Response, db: Session = Depends(get_db), session: Optional[str] = Cookie(None)):
    user_session = get_user_session(request, response, session)
    clear_cart(db, user_session)
    return {"success": True, "message": "Корзина очищена"}
