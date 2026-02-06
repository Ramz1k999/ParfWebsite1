# parse_and_import_optimized.py
import os
import sys
import requests
from bs4 import BeautifulSoup
import time
import re
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
import getpass

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
    
    if "login" in response.url.lower():
        print("❌ Ошибка авторизации")
        return False
    
    test = session.get("https://perforyou.ru/?nav=1")
    if "js-product" in test.text:
        print("✓ Авторизация успешна!")
        
        soup = BeautifulSoup(test.content, 'html.parser')
        first_price = soup.find('tr', class_='js-product')
        if first_price:
            price_text = first_price.find_all('td')[1].text.strip()
            print(f"Пример цены: {price_text}")
        
        return True
    else:
        print("❌ Не удалось получить доступ к товарам")
        return False

def parse_price_rub(price_str):
    """Парсит цену из формата '47,5 руб.' в число"""
    try:
        price_clean = re.sub(r'[^\d,]', '', price_str)
        price_clean = price_clean.replace(',', '.')
        return Decimal(price_clean) if price_clean else Decimal('0.00')
    except:
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

def bulk_save_products(products_batch, db, markup_percent=20):
    """Массовое сохранение товаров (быстрее)"""
    imported_count = 0
    error_count = 0
    error_log = []
    
    products_to_insert = []
    
    for product_data in products_batch:
        try:
            name = product_data['name']
            price_rub_str = product_data['price_rub']
            product_id = product_data.get('id', 'unknown')
            
            base_price = parse_price_rub(price_rub_str)
            
            if base_price == Decimal('0.00'):
                error_count += 1
                error_log.append(f"ID:{product_id} | Нулевая цена: '{price_rub_str}'")
                continue
            
            final_price = apply_markup(base_price, markup_percent)
            
            products_to_insert.append({
                'name': name,
                'price_rub': final_price
            })
            
        except Exception as e:
            error_count += 1
            error_log.append(f"ID:{product_id} | Ошибка: {str(e)}")
    
    # Массовая вставка
    if products_to_insert:
        try:
            db.bulk_insert_mappings(Product, products_to_insert)
            imported_count = len(products_to_insert)
        except Exception as e:
            print(f"  ❌ Ошибка bulk insert: {e}")
            # Откат к обычной вставке
            for product in products_to_insert:
                try:
                    existing = db.query(Product).filter(Product.name == product['name']).first()
                    if not existing:
                        db.add(Product(**product))
                        imported_count += 1
                except:
                    error_count += 1
    
    return imported_count, error_count, error_log

def main():
    print("="*60)
    print("  Парсинг и импорт товаров (ОПТИМИЗИРОВАННЫЙ)")
    print("="*60)
    
    Base.metadata.create_all(bind=engine)
    
    print("\n=== АВТОРИЗАЦИЯ ===")
    username = input("Логин: ").strip()
    password = getpass.getpass("Пароль: ")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    if not login(session, username, password):
        return
    
    print("\n=== НАСТРОЙКИ ===")
    markup_percent = input("Наценка % (Enter для 20%): ").strip()
    markup_percent = int(markup_percent) if markup_percent else 20
    
    max_pages = input("Макс. страниц (Enter для 9999): ").strip()
    max_pages = int(max_pages) if max_pages else 9999
    
    batch_size = input("Размер батча страниц (Enter для 20): ").strip()
    batch_size = int(batch_size) if batch_size else 20
    
    pause = input("Пауза между запросами в сек (Enter для 0.5): ").strip()
    pause = float(pause) if pause else 0.5
    
    print(f"\n✓ Наценка: +{markup_percent}%")
    print(f"✓ Батч: {batch_size} страниц")
    print(f"✓ Пауза: {pause} сек")
    
    confirm = input("\nНачать импорт? (да/нет): ")
    if confirm.lower() not in ['да', 'yes', 'y', 'д']:
        print("Отменено")
        return
    
    db = SessionLocal()
    
    print("\n" + "="*60)
    print("Начинаем парсинг и импорт...")
    print("="*60 + "\n")
    
    total_imported = 0
    total_errors = 0
    total_parsed = 0
    empty_pages = 0
    start_time = time.time()
    all_error_logs = []
    
    products_buffer = []
    
    try:
        for page in range(1, max_pages + 1):
            print(f"[{page}/{max_pages}] ", end='')
            
            products = parse_page(page, session)
            
            if not products:
                empty_pages += 1
                print("⚠ Пустая")
                
                if empty_pages >= 5:
                    print("\n✓ Конец каталога")
                    break
            else:
                empty_pages = 0
                total_parsed += len(products)
                products_buffer.extend(products)
                print(f"✓ +{len(products)}", end='')
                
                # Сохраняем батчами
                if len(products_buffer) >= batch_size * 50:  # ~50 товаров на страницу
                    imported, errors, error_log = bulk_save_products(products_buffer, db, markup_percent)
                    db.commit()
                    
                    total_imported += imported
                    total_errors += errors
                    all_error_logs.extend(error_log)
                    
                    print(f" | Батч сохранён: {imported} товаров")
                    products_buffer = []
                else:
                    print()
            
            time.sleep(pause)
            
            # Прогресс каждые 100 страниц
            if page % 100 == 0:
                elapsed = time.time() - start_time
                rate = page / elapsed * 60
                remaining = (max_pages - page) / rate if rate > 0 else 0
                print(f"  📊 Прогресс | Спарсено: {total_parsed} | В БД: {total_imported} | ~{int(remaining)} мин\n")
        
        # Сохраняем остаток
        if products_buffer:
            imported, errors, error_log = bulk_save_products(products_buffer, db, markup_percent)
            db.commit()
            total_imported += imported
            total_errors += errors
            all_error_logs.extend(error_log)
        
        elapsed = time.time() - start_time
        
        print("\n" + "="*60)
        print("✓ ИМПОРТ ЗАВЕРШЁН")
        print(f"  Спарсено товаров: {total_parsed}")
        print(f"  Добавлено в БД: {total_imported}")
        print(f"  Пропущено/ошибок: {total_errors}")
        print(f"  Время: {int(elapsed/60)} мин {int(elapsed%60)} сек")
        print(f"  Скорость: {int(total_parsed/(elapsed/60))} товаров/мин")
        print("="*60)
        
        # Лог ошибок
        if all_error_logs:
            with open('import_errors.log', 'w', encoding='utf-8') as f:
                f.write(f"Всего ошибок: {len(all_error_logs)}\n\n")
                for i, error in enumerate(all_error_logs, 1):
                    f.write(f"{i}. {error}\n")
            
            print(f"\n⚠ Лог ошибок: import_errors.log")
            print("Первые 10 ошибок:")
            for error in all_error_logs[:10]:
                print(f"  • {error}")
    
    except KeyboardInterrupt:
        print("\n\n⚠ Прервано")
        db.commit()
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    main()
