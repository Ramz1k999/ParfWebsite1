from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import hashlib
import secrets
import time
from app.database import get_db
from app.schemas.user import Token, UserResponse
from app.crud.user import authenticate_user
from app.auth.jwt import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from app.models.user import User, UserRole

router = APIRouter()

# Генерируем случайный токен для защиты эндпоинта
SETUP_TOKEN = secrets.token_urlsafe(32)
SETUP_EXPIRY = time.time() + 3600  # Токен действителен 1 час

# Выводим токен в консоль при импорте модуля
print(f"\n\n=== SETUP TOKEN ===\n{SETUP_TOKEN}\n==================\n\n")


@router.post("/login", response_model=Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """Вход в систему и получение токена доступа"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Учетная запись неактивна"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return current_user


@router.post("/setup-admin")
async def setup_admin(
        request: Request,
        token: str,
        db: Session = Depends(get_db)
):
    """Временный эндпоинт для создания администратора"""
    # Проверяем токен и время действия
    if token != SETUP_TOKEN or time.time() > SETUP_EXPIRY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недействительный или истекший токен"
        )

    # Проверяем, существует ли уже администратор
    admin = db.query(User).filter(User.email == "admin@example.com").first()
    if admin:
        # Обновляем существующего администратора
        password = "admin"
        salt = "salt"
        hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

        admin.email = "admin@example.com"
        admin.username = "admin"
        admin.hashed_password = hashed
        admin.salt = salt
        admin.full_name = "System Administrator"
        admin.is_active = True
        admin.role = UserRole.SUPERADMIN

        db.commit()
        return {"message": "Администратор обновлен", "email": "admin@example.com", "password": "admin"}
    else:
        # Создаем нового администратора
        password = "admin"
        salt = "salt"
        hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

        admin = User(
            email="admin@example.com",
            username="admin",
            hashed_password=hashed,
            salt=salt,
            full_name="System Administrator",
            is_active=True,
            role=UserRole.SUPERADMIN
        )

        db.add(admin)
        db.commit()

        return {"message": "Администратор создан", "email": "admin@example.com", "password": "admin"}


@router.post("/execute-sql")
async def execute_sql(
        request: Request,
        token: str,
        sql: str,
        db: Session = Depends(get_db)
):
    """Временный эндпоинт для выполнения SQL-запроса"""
    # Проверяем токен и время действия
    if token != SETUP_TOKEN or time.time() > SETUP_EXPIRY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недействительный или истекший токен"
        )

    try:
        # Выполняем SQL-запрос
        from sqlalchemy import text
        result = db.execute(text(sql))
        db.commit()

        # Пытаемся получить результаты
        try:
            rows = result.fetchall()
            return {"message": "SQL-запрос выполнен успешно", "rows": [dict(row) for row in rows]}
        except:
            return {"message": "SQL-запрос выполнен успешно"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}