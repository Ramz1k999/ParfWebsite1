import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.models.product import Product
from app.models.currency import CurrencyRate
from app.database import SessionLocal


def create_test_data():
    db = SessionLocal()

    try:
        # Проверяем есть ли уже данные
        existing_products = db.query(Product).first()
        if existing_products:
            print("Данные уже существуют!")
            return

        print("Добавляем тестовые данные...")

        # Добавляем курс доллара
        usd_rate = CurrencyRate(
            currency_code="USD",
            rate_to_rub=95.50,
            is_active=True
        )
        db.add(usd_rate)

        # Товары без product_type
        products = [
            Product(
                name="Пакет TOM FORD большой 26 x31",
                price_rub=265.0,
                brand="TOM FORD",
                volume="26 x31"
            ),
            Product(
                name="Tom Ford - Black Orchid Туалетная вода 1.5 мл",
                price_rub=265.0,
                brand="Tom Ford",
                volume="1.5 мл"
            ),
            Product(
                name="Tom Ford BLACK ORCHID 1,5ml edt",
                price_rub=291.5,
                brand="Tom Ford",
                volume="1.5 мл"
            ),
            Product(
                name="Tom Ford Velvet Orchid edp 2 ml ОТЛИВАНТ",
                price_rub=300.4,
                brand="Tom Ford",
                volume="2 мл"
            ),
            Product(
                name="Tom Ford BLACK ORCHID 1.5ml edT Sample",
                price_rub=309.2,
                brand="Tom Ford",
                volume="1.5 мл"
            )
        ]

        for product in products:
            db.add(product)

        db.commit()
        print(f"✅ Успешно добавлено:")
        print(f"   - Товаров: {len(products)}")
        print(f"   - Курс USD: 95.50 руб.")

    except Exception as e:
        print(f"❌ Ошибка при добавлении данных: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_test_data()