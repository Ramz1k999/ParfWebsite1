from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.schemas.user import Token, UserResponse
from app.crud.user import authenticate_user
from app.auth.jwt import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """Вход в систему и получение токена доступа"""
    print(f"Попытка входа с username: {form_data.username}")
    
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        print(f"Аутентификация не удалась для username: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    print(f"Аутентификация успешна для пользователя: {user.email} (роль: {user.role})")
    
    if not user.is_active:
        print(f"Пользователь {user.email} неактивен")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Учетная запись неактивна"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    print(f"Токен создан для пользователя: {user.email}")

    # Возвращаем ответ с явными CORS-заголовками
    response = JSONResponse(
        content={"access_token": access_token, "token_type": "bearer"}
    )
    response.headers["Access-Control-Allow-Origin"] = "https://src-tjpz.onrender.com"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response


@router.get("/me", response_model=UserResponse)
async def read_users_me(request: Request, current_user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    print(f"Запрос данных пользователя: {current_user.email}")
    
    # Преобразуем модель в словарь
    user_dict = {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "role": current_user.role,
        "is_admin": current_user.is_admin,
        "is_superadmin": current_user.is_superadmin
    }
    
    # Возвращаем ответ с явными CORS-заголовками
    response = JSONResponse(content=user_dict)
    response.headers["Access-Control-Allow-Origin"] = "https://src-tjpz.onrender.com"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response


@router.options("/{path:path}")
async def options_handler(request: Request, path: str):
    """
    Обработчик для OPTIONS-запросов, необходимых для CORS.
    """
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "https://src-tjpz.onrender.com",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )
