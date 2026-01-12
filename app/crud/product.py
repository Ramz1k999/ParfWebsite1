from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.product import Product
from app.models.currency import CurrencyRate
from typing import List, Optional
from app.cache import cache


@cache(ttl_seconds=60 * 5)  # Кэшируем на 5 минут
def get_all_products(db: Session, skip: int = 0, limit: int = 100) -> List[Product]:
    """
    Получить все товары с пагинацией.

    Args:
        db: Сессия базы данных
        skip: Сколько записей пропустить
        limit: Максимальное количество записей

    Returns:
        List[Product]: Список товаров
    """
    return db.query(Product).offset(skip).limit(limit).all()


@cache(ttl_seconds=60 * 5)
def count_products(db: Session) -> int:
    """
    Получить общее количество товаров.

    Args:
        db: Сессия базы данных

    Returns:
        int: Количество товаров
    """
    return db.query(Product).count()


def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
    """
    Получить товар по ID.

    Args:
        db: Сессия базы данных
        product_id: ID товара

    Returns:
        Optional[Product]: Товар или None, если товар не найден
    """
    return db.query(Product).filter(Product.id == product_id).first()


def create_product(
        db: Session,
        name: str,
        price_rub: float,
        description: Optional[str] = None,
        brand: Optional[str] = None,
        volume: Optional[str] = None
) -> Product:
    """
    Создать новый товар.

    Args:
        db: Сессия базы данных
        name: Название товара
        price_rub: Цена в рублях
        description: Описание товара
        brand: Бренд
        volume: Объем

    Returns:
        Product: Созданный товар
    """
    db_product = Product(
        name=name,
        price_rub=price_rub,
        description=description,
        brand=brand,
        volume=volume
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def update_product(
        db: Session,
        product_id: int,
        name: Optional[str] = None,
        price_rub: Optional[float] = None,
        description: Optional[str] = None,
        brand: Optional[str] = None,
        volume: Optional[str] = None
) -> Optional[Product]:
    """
    Обновить товар.

    Args:
        db: Сессия базы данных
        product_id: ID товара
        name: Новое название товара
        price_rub: Новая цена в рублях
        description: Новое описание товара
        brand: Новый бренд
        volume: Новый объем

    Returns:
        Optional[Product]: Обновленный товар или None, если товар не найден
    """
    product = get_product_by_id(db, product_id)
    if not product:
        return None

    if name is not None:
        product.name = name
    if price_rub is not None:
        product.price_rub = price_rub
    if description is not None:
        product.description = description
    if brand is not None:
        product.brand = brand
    if volume is not None:
        product.volume = volume

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> bool:
    """
    Удалить товар.

    Args:
        db: Сессия базы данных
        product_id: ID товара

    Returns:
        bool: True если товар удален, иначе False
    """
    product = get_product_by_id(db, product_id)
    if not product:
        return False

    db.delete(product)
    db.commit()
    return True


def convert_price(db: Session, price_rub: float, currency: str = "RUB") -> float:
    """
    Конвертировать цену в указанную валюту.

    Args:
        db: Сессия базы данных
        price_rub: Цена в рублях
        currency: Валюта для конвертации (RUB или USD)

    Returns:
        float: Цена в указанной валюте

    Raises:
        ValueError: Если валюта не поддерживается
    """
    if currency == "RUB":
        return price_rub
    elif currency == "USD":
        # Получаем курс доллара
        rate = db.query(CurrencyRate).filter(CurrencyRate.code == "USD").first()
        if rate:
            return price_rub / float(rate.rate)
        else:
            # Если курс не найден, используем фиксированный курс
            return price_rub / 75.0
    else:
        raise ValueError(f"Неподдерживаемая валюта: {currency}")


def search_products(
        db: Session,
        title: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: str = "name",
        sort_dir: str = "asc",
        skip: int = 0,
        limit: int = 50
) -> List[Product]:
    """
    Расширенный поиск товаров с фильтрацией и сортировкой.

    Args:
        db: Сессия базы данных
        title: Фильтр по названию (частичное совпадение)
        brand: Фильтр по бренду (частичное совпадение)
        min_price: Минимальная цена
        max_price: Максимальная цена
        sort_by: Поле для сортировки (name, price, date)
        sort_dir: Направление сортировки (asc, desc)
        skip: Сколько записей пропустить
        limit: Максимальное количество записей

    Returns:
        List[Product]: Список товаров, соответствующих критериям
    """
    query = db.query(Product)

    # Применяем фильтры
    if title:
        query = query.filter(Product.name.ilike(f"%{title}%"))
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))
    if min_price is not None:
        query = query.filter(Product.price_rub >= min_price)
    if max_price is not None:
        query = query.filter(Product.price_rub <= max_price)

    # Применяем сортировку
    if sort_by == "name":
        if sort_dir == "asc":
            query = query.order_by(Product.name)
        else:
            query = query.order_by(desc(Product.name))
    elif sort_by == "price":
        if sort_dir == "asc":
            query = query.order_by(Product.price_rub)
        else:
            query = query.order_by(desc(Product.price_rub))
    elif sort_by == "date":
        if sort_dir == "asc":
            query = query.order_by(Product.created_at)
        else:
            query = query.order_by(desc(Product.created_at))

    # Применяем пагинацию
    return query.offset(skip).limit(limit).all()


def count_search_results(
        db: Session,
        title: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
) -> int:
    """
    Подсчет количества товаров, соответствующих критериям поиска.

    Args:
        db: Сессия базы данных
        title: Фильтр по названию (частичное совпадение)
        brand: Фильтр по бренду (частичное совпадение)
        min_price: Минимальная цена
        max_price: Максимальная цена

    Returns:
        int: Количество товаров
    """
    query = db.query(Product)

    # Применяем фильтры
    if title:
        query = query.filter(Product.name.ilike(f"%{title}%"))
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))
    if min_price is not None:
        query = query.filter(Product.price_rub >= min_price)
    if max_price is not None:
        query = query.filter(Product.price_rub <= max_price)

    return query.count()


def get_unique_brands(db: Session) -> List[str]:
    """
    Получить список уникальных брендов.

    Args:
        db: Сессия базы данных

    Returns:
        List[str]: Список уникальных брендов
    """
    brands = db.query(Product.brand).filter(Product.brand != None).distinct().all()
    return [brand[0] for brand in brands if brand[0]]


def get_price_range(db: Session) -> tuple:
    """
    Получить минимальную и максимальную цену товаров.

    Args:
        db: Сессия базы данных

    Returns:
        tuple: (min_price, max_price)
    """
    min_price = db.query(func.min(Product.price_rub)).scalar() or 0
    max_price = db.query(func.max(Product.price_rub)).scalar() or 0
    return (min_price, max_price)