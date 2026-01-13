# create_superadmin.py
import os
import sys
from sqlalchemy.orm import Session

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.crud.user import get_user_by_email, create_user


def create_superadmin():
    """Создает суперадмина, если он не существует"""
    # Создаем сессию базы данных
    db = SessionLocal()
    try:
        # Проверяем, существует ли уже суперадмин
        email = "jalol@example.com"  # Замените на нужный email
        existing_user = get_user_by_email(db, email)

        if existing_user:
            if existing_user.role == UserRole.SUPERADMIN:
                print(f"Суперадмин с email {email} уже существует.")
                return
            else:
                print(f"Пользователь с email {email} существует, но не является суперадмином.")
                return

        # Создаем суперадмина
        superadmin = create_user(
            db=db,
            email=email,
            username="jalol",  # Замените на нужное имя пользователя
            password="admin123!",  # Замените на надежный пароль
            full_name="Super Administrator",
            notes="Автоматически созданный суперадминистратор",
            role=UserRole.SUPERADMIN
        )

        print(f"Суперадмин успешно создан с ID: {superadmin.id}")

    except Exception as e:
        print(f"Ошибка при создании суперадмина: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    # Убедитесь, что все таблицы созданы
    Base.metadata.create_all(bind=engine)
    create_superadmin()