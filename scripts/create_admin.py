import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.user import User, Base
from app.crud.user import get_user_by_email, create_user


def create_initial_admin():
    """Создает таблицы и первого администратора, если он не существует"""
    # Создаем таблицы
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Проверяем, существует ли администратор
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        existing_admin = get_user_by_email(db, admin_email)

        if existing_admin:
            print(f"Администратор с email {admin_email} уже существует")
            return

        # Создаем администратора
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        admin_username = os.getenv("ADMIN_USERNAME", "admin")

        admin = create_user(
            db=db,
            email=admin_email,
            username=admin_username,
            password=admin_password,
            full_name="Администратор системы",
            is_admin=True
        )

        print(f"Администратор создан успешно: {admin_email}")
        print(f"ID: {admin.id}, Имя пользователя: {admin.username}")

    except Exception as e:
        print(f"Ошибка при создании администратора: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    create_initial_admin()