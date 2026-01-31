# create_tables.py
"""
Скрипт для создания всех таблиц в базе данных.
Запуск: python create_tables.py
"""

from app.database import Base, engine

# Импортируем все модели, чтобы SQLAlchemy знал о них
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.cart import CartItem
from app.models.currency import CurrencyRate


def create_tables():
    """Создает все таблицы в базе данных"""
    print("🔄 Начинаю создание таблиц в базе данных...")
    print(f"📍 Подключение к: {engine.url}")
    
    try:
        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)
        
        print("\n✅ Таблицы успешно созданы!")
        print("\n📋 Созданные таблицы:")
        print("   - users (пользователи)")
        print("   - products (товары)")
        print("   - orders (заказы)")
        print("   - order_items (позиции заказов)")
        print("   - cart_items (корзина)")
        print("   - currency_rates (курсы валют)")
        
    except Exception as e:
        print(f"\n❌ Ошибка при создании таблиц: {e}")
        raise


def drop_tables():
    """ВНИМАНИЕ: Удаляет все таблицы! Используйте с осторожностью!"""
    print("⚠️  ВНИМАНИЕ: Это удалит ВСЕ таблицы и данные!")
    confirm = input("Вы уверены? Введите 'YES' для подтверждения: ")
    
    if confirm == "YES":
        print("🔄 Удаление таблиц...")
        Base.metadata.drop_all(bind=engine)
        print("✅ Таблицы удалены")
    else:
        print("❌ Отменено")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        drop_tables()
    else:
        create_tables()
