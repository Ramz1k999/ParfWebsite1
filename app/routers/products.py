from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductDetail, ProductListItem, ProductListResponse
from app.crud.product import get_all_products, get_product_by_id, create_product, update_product, delete_product, \
    count_products, convert_price, search_products, count_search_results, get_unique_brands, get_price_range
from app.auth.jwt import get_current_admin_user
from app.models.user import User
from app.logger import api_logger

router = APIRouter()


@router.get("/products", response_model=ProductListResponse)
async def read_products(
        currency: str = Query("RUB", description="Валюта (USD/RUB)"),
        page: int = Query(1, ge=1, description="Номер страницы"),
        per_page: int = Query(50, ge=1, le=100, description="Товаров на странице"),
        db: Session = Depends(get_db)
):
    """Получить список всех товаров с пагинацией"""
    try:
        offset = (page - 1) * per_page
        products = get_all_products(db, skip=offset, limit=per_page)
        total_count = count_products(db)

        product_items = []
        for product in products:
            try:
                converted_price = convert_price(db, float(product.price_rub), currency)
                currency_symbol = "руб." if currency == "RUB" else "$"

                item = ProductListItem(
                    id=product.id,
                    name=product.name,
                    price=converted_price,
                    price_formatted=f"{converted_price:,.1f} {currency_symbol}",
                    currency=currency_symbol,
                    updated_date=product.updated_at.strftime("%d.%m.%Y"),
                    default_quantity=1,
                    brand=product.brand,
                    volume=product.volume
                )
                product_items.append(item)

            except ValueError:
                # Обработка ошибки конвертации цены
                api_logger.error(f"Ошибка конвертации цены для товара {product.id}")
                pass

        return ProductListResponse(
            products=product_items,
            total_count=total_count,
            current_page=page,
            per_page=per_page,
            has_next=offset + per_page < total_count,
            has_prev=page > 1
        )

    except Exception as e:
        api_logger.error(f"Ошибка при получении списка товаров: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@router.get("/products/search", response_model=ProductListResponse)
async def search_products_api(
        title: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        currency: str = Query("RUB", description="Валюта (USD/RUB)"),
        sort_by: str = Query("name", description="Поле для сортировки (name/price/date)"),
        sort_dir: str = Query("asc", description="Направление сортировки (asc/desc)"),
        page: int = Query(1, ge=1, description="Номер страницы"),
        per_page: int = Query(50, ge=1, le=100, description="Товаров на странице"),
        db: Session = Depends(get_db)
):
    """Расширенный поиск товаров"""
    try:
        api_logger.info(f"Поиск товаров: title={title}, brand={brand}, min_price={min_price}, max_price={max_price}")

        offset = (page - 1) * per_page

        products = search_products(
            db,
            title=title,
            brand=brand,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            sort_dir=sort_dir,
            skip=offset,
            limit=per_page
        )

        total_count = count_search_results(
            db,
            title=title,
            brand=brand,
            min_price=min_price,
            max_price=max_price
        )

        product_items = []
        for product in products:
            try:
                converted_price = convert_price(db, float(product.price_rub), currency)
                currency_symbol = "руб." if currency == "RUB" else "$"

                item = ProductListItem(
                    id=product.id,
                    name=product.name,
                    price=converted_price,
                    price_formatted=f"{converted_price:,.1f} {currency_symbol}",
                    currency=currency_symbol,
                    updated_date=product.updated_at.strftime("%d.%m.%Y"),
                    default_quantity=1,
                    brand=product.brand,
                    volume=product.volume
                )
                product_items.append(item)

            except ValueError:
                # Обработка ошибки конвертации цены
                api_logger.error(f"Ошибка конвертации цены для товара {product.id}")
                pass

        return ProductListResponse(
            products=product_items,
            total_count=total_count,
            current_page=page,
            per_page=per_page,
            has_next=offset + per_page < total_count,
            has_prev=page > 1
        )

    except Exception as e:
        api_logger.error(f"Ошибка при поиске товаров: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@router.get("/products/filters")
async def get_filters(db: Session = Depends(get_db)):
    """Получить данные для фильтров (бренды, диапазон цен)"""
    try:
        brands = get_unique_brands(db)
        min_price, max_price = get_price_range(db)

        return {
            "brands": brands,
            "price_range": {
                "min": min_price,
                "max": max_price
            }
        }
    except Exception as e:
        api_logger.error(f"Ошибка при получении данных для фильтров: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@router.get("/products/{product_id}", response_model=ProductDetail)
async def read_product(product_id: int, currency: str = "RUB", db: Session = Depends(get_db)):
    """Получить детальную информацию о товаре по ID"""
    product = get_product_by_id(db, product_id)
    if product is None:
        api_logger.warning(f"Товар с ID {product_id} не найден")
        raise HTTPException(status_code=404, detail="Товар не найден")

    try:
        # Конвертируем цену в нужную валюту
        converted_price = convert_price(db, float(product.price_rub), currency)
        currency_symbol = "руб." if currency == "RUB" else "$"

        # Создаем объект с детальной информацией о товаре
        product_detail = ProductDetail(
            id=product.id,
            name=product.name,
            price=converted_price,
            price_formatted=f"{converted_price:,.1f} {currency_symbol}",
            currency=currency_symbol,
            description=product.description,
            brand=product.brand,
            volume=product.volume,
            created_at=product.created_at,
            updated_at=product.updated_at
        )

        return product_detail
    except ValueError as e:
        api_logger.error(f"Ошибка при получении информации о товаре {product_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/products", response_model=ProductDetail, status_code=status.HTTP_201_CREATED)
async def create_product_api(
        product_data: ProductCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_admin_user)
):
    """Создать новый товар (только для администраторов)"""
    try:
        api_logger.info(f"Создание нового товара: {product_data.name}")


        new_product = create_product(
            db=db,
            name=product_data.name,
            price_rub=product_data.price_rub,
            description=product_data.description,
            brand=product_data.brand,
            volume=product_data.volume
        )

        # Конвертируем цену для ответа
        currency = "RUB"
        currency_symbol = "руб."

        return ProductDetail(
            id=new_product.id,
            name=new_product.name,
            price=float(new_product.price_rub),
            price_formatted=f"{float(new_product.price_rub):,.1f} {currency_symbol}",
            currency=currency_symbol,
            description=new_product.description,
            brand=new_product.brand,
            volume=new_product.volume,
            created_at=new_product.created_at,
            updated_at=new_product.updated_at
        )
    except Exception as e:
        api_logger.error(f"Ошибка при создании товара: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при создании товара: {str(e)}")

@router.put("/admin/products/{product_id}", response_model=ProductDetail)
async def update_product_api(
        product_id: int,
        product_data: ProductUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_admin_user)
):
    """Обновить товар (только для администраторов)"""
    api_logger.info(f"Обновление товара с ID {product_id}")


    updated_product = update_product(
        db=db,
        product_id=product_id,
        name=product_data.name,
        price_rub=product_data.price_rub,
        description=product_data.description,
        brand=product_data.brand,
        volume=product_data.volume
    )

    if updated_product is None:
        api_logger.warning(f"Товар с ID {product_id} не найден при попытке обновления")
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Конвертируем цену для ответа
    currency = "RUB"
    currency_symbol = "руб."

    return ProductDetail(
        id=updated_product.id,
        name=updated_product.name,
        price=float(updated_product.price_rub),
        price_formatted=f"{float(updated_product.price_rub):,.1f} {currency_symbol}",
        currency=currency_symbol,
        description=updated_product.description,
        brand=updated_product.brand,
        volume=updated_product.volume,
        created_at=updated_product.created_at,
        updated_at=updated_product.updated_at
    )


@router.delete("/admin/products/{product_id}")
async def delete_product_api(
        product_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_admin_user)
):
    """Удалить товар (только для администраторов)"""
    api_logger.info(f"Удаление товара с ID {product_id}")

    success = delete_product(db, product_id)
    if not success:
        api_logger.warning(f"Товар с ID {product_id} не найден при попытке удаления")
        raise HTTPException(status_code=404, detail="Товар не найден")

    return {"message": "Товар успешно удален"}