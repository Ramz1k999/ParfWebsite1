# parse_and_import.py
import os
import sys
import requests
from bs4 import BeautifulSoup
import time
import re
from decimal import Decimal
from sqlalchemy.orm import Session
import getpass

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models.product import Product

def login(session, username, password):
    """Авторизация на сайте"""
    login_url = "https://perforyou.ru/login/"
    
    login_data = {
        'login-name': username,
        'login-pass': password,
        'login-remember': 'on'
    }
    
    print("Попытка авторизации...")
    response = session.post(login_url, data=login_data, allow_redirects=True)
    
    print(f"Status: {response.status_code}")
    print(f"URL после логина: {response.url}")
    
    # Проверяем успешность
    if "login" in response.url.lower():
        print("❌ Ошибка авторизации. Проверьте логин и пароль.")
        return False
    
    # Проверяем что есть товары
    test = session.get("https://perforyou.ru/?nav=1")
    if "js-product" in test.text:
        print("✓ Авторизация успешна!")
        
        # Проверяем валюту
        soup = BeautifulSoup(test.content, 'html.parser')
        first_price = soup.find('tr', class_='js-product')
        if first_price:
            price_text = first_price.find_all('td')[1].text.strip()
            print(f"Пример цены: {price_text}")
            
            if 'руб' in price_text.lower():
                print("✓ Валюта: рубли")
            elif '$' in price_text:
                print("⚠ Валюта: доллары (может потребоваться переключение)")
        
        return True
    else:
        print("❌ Не удалось получить доступ к товарам")
        return False

def parse_price_rub(price_str):
    """Парсит цену из формата '47,5 руб.' в число"""
    try:
        price_clean = re.sub(r'[^\d,.]', '', price_str)
        price_clean = price_clean.replace(',', '.')
        return Decimal(price_clean)
    except Exception as e:
        print(f"⚠ Ошибка парсинга цены '{price_str}': {e}")
        return Decimal('0.00')

def apply_markup(price, markup_percent=20):
    """Добавляет наценку к цене"""
    markup_multiplier = Decimal('1') + (Decimal(str(markup_percent)) / Decimal('100'))
    return (price * markup_multiplier).quantize(Decimal('0.01'))

def parse_page(page_num, session):
    """Парсит одну страницу товаров"""
    url = f"https://perforyou.ru/?nav={page_num}"
    
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        products = []
        rows = soup.find_all('tr', class_='js-product')
        
        if not rows:
            return []
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                product = {
                    'id': row.get('data-id', ''),
                    'name': cells[0].text.strip(),
                    'price_rub': cells[1].text.strip()
                }
                products.append(product)
        
        return products
    
    except Exception as e:
        print(f"Ошибка на странице {page_num}: {e}")
        return []

def save_products_to_db(products, db, markup_percent=20):
    """Сохраняет товары в БД с наценкой"""
    imported_count = 0
    updated_count = 0
    error_count = 0
    
    for product_data in products:
        try:
            name = product_data['name']
            price_rub_str = product_data['price_rub']
            
            # Парсим и добавляем наценку
            base_price = parse_price_rub(price_rub_str)
            final_price = apply_markup(base_price, markup_percent)
            
            # Проверяем существование
            existing_product = db.query(Product).filter(Product.name == name).first()
            
            if existing_product:
                existing_product.price_rub = final_price
                updated_count += 1
            else:
                new_product = Product(
                    name=name,
                    price_rub=final_price
                )
                db.add(new_product)
                imported_count += 1
        
        except Exception as e:
            error_count += 1
            print(f"❌ Ошибка сохранения: {e}")
    
    return imported_count, updated_count, error_count

def main():
    print("="*60)
    print("  Парсинг и импорт товаров perforyou.ru → БД")
    print("="*60)
    
    # Создаём таблицы если нужно
    Base.metadata.create_all(bind=engine)
    
    # Настройки
    print("\n=== АВТОРИЗАЦИЯ ===")
    username = input("Логин: ").strip()
    password = getpass.getpass("Пароль: ")
    
    # Создаём сессию
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # Авторизуемся
    if not login(session, username, password):
        return
    
    print("\n=== НАСТРОЙКИ ИМПОРТА ===")
    markup_percent = input("Наценка в % (Enter для 20%): ").strip()
    markup_percent = int(markup_percent) if markup_percent else 20
    
    max_pages = input("Макс. страниц (Enter для 9999): ").strip()
    max_pages = int(max_pages) if max_pages else 9999
    
    print(f"\n✓ Наценка: +{markup_percent}%")
    
    confirm = input("\nНачать импорт? (да/нет): ")
    if confirm.lower() not in ['да', 'yes', 'y', 'д']:
        print("Отменено")
        return
    
    # Создаём БД сессию
    db = SessionLocal()
    
    print("\n" + "="*60)
    print("Начинаем парсинг и импорт...")
    print("="*60 + "\n")
    
    total_imported = 0
    total_updated = 0
    total_errors = 0
    empty_pages = 0
    start_time = time.time()
    
    try:
        for page in range(1, max_pages + 1):
            print(f"[{page}/{max_pages}] Страница {page}...", end=' ')
            
            # Парсим страницу
            products = parse_page(page, session)
            
            if not products:
                empty_pages += 1
                print("⚠ Пустая")
                
                if empty_pages >= 5:
                    print("\n✓ Достигнут конец каталога")
                    break
            else:
                empty_pages = 0
                
                # Сохраняем в БД
                imported, updated, errors = save_products_to_db(products, db, markup_percent)
                total_imported += imported
                total_updated += updated
                total_errors += errors
                
                print(f"✓ +{imported} новых, ~{updated} обновл | Всего: {total_imported + total_updated}")
                
                # Коммит каждые 10 страниц
                if page % 10 == 0:
                    db.commit()
                    elapsed = time.time() - start_time
                    print(f"  💾 Сохранено в БД | ⏱ {int(elapsed/60)} мин\n")
            
            # Пауза между запросами
            time.sleep(2)
        
        # Финальный коммит
        db.commit()
        
        elapsed = time.time() - start_time
        
        print("\n" + "="*60)
        print("✓ ИМПОРТ ЗАВЕРШЁН")
        print(f"  Новых товаров: {total_imported}")
        print(f"  Обновлено: {total_updated}")
        print(f"  Ошибок: {total_errors}")
        print(f"  Всего в БД: {total_imported + total_updated}")
        print(f"  Время: {int(elapsed/60)} мин {int(elapsed%60)} сек")
        print(f"  Наценка: +{markup_percent}%")
        print("="*60)
    
    except KeyboardInterrupt:
        print("\n\n⚠ Прервано (Ctrl+C)")
        db.commit()
        print(f"Сохранено: {total_imported + total_updated} товаров")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    main()
