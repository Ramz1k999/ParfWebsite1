# app/routers/admin_users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserListResponse, UserListItem, UserUpdate, UserPasswordChange, \
    UserRole
from app.crud.user import create_user, get_user_by_email, get_user_by_username, get_all_users, update_user, \
    change_user_password, count_users, get_user_by_id
from app.auth.jwt import get_current_admin_user, get_current_superadmin_user
from app.models.user import User

router = APIRouter()


@router.post("/users", response_model=UserResponse)
async def admin_create_user(
        user_data: UserCreate,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """Создание нового пользователя (только для администраторов)"""
    # Проверяем, что email не занят
    db_user = get_user_by_email(db, user_data.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email уже зарегистрирован"
        )

    # Проверяем, что username не занят
    db_user = get_user_by_username(db, user_data.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя пользователя уже занято"
        )

    # Проверяем права на создание пользователя с определенной ролью
    if user_data.role != UserRole.USER and not current_admin.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только суперадминистратор может создавать администраторов"
        )

    # Создаем пользователя
    return create_user(
        db=db,
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        full_name=user_data.full_name,
        notes=user_data.notes,
        role=user_data.role,
        created_by=current_admin.id
    )


@router.get("/users", response_model=UserListResponse)
async def admin_get_users(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        _: User = Depends(get_current_admin_user)
):
    """Получить список всех пользователей (только для администраторов)"""
    users = get_all_users(db, skip=skip, limit=limit)
    total = count_users(db)

    return UserListResponse(
        users=[UserListItem.from_orm(user) for user in users],
        total_count=total
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def admin_get_user(
        user_id: int,
        db: Session = Depends(get_db),
        _: User = Depends(get_current_admin_user)
):
    """Получить информацию о пользователе по ID (только для администраторов)"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def admin_update_user(
        user_id: int,
        user_data: UserUpdate,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """Обновить данные пользователя (только для администраторов)"""
    # Проверяем, что пользователь существует
    existing_user = get_user_by_id(db, user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    # Проверяем права на изменение роли
    if user_data.role is not None:
        # Если меняем роль на админа или суперадмина
        if user_data.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            # Только суперадмин может назначать админов и суперадминов
            if not current_admin.is_superadmin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Только суперадминистратор может назначать администраторов"
                )

        # Если меняем роль суперадмина
        if existing_user.role == UserRole.SUPERADMIN:
            # Только суперадмин может менять роль другого суперадмина
            if not current_admin.is_superadmin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Только суперадминистратор может изменять роль суперадминистратора"
                )

    # Проверяем, что email не занят другим пользователем
    if user_data.email and user_data.email != existing_user.email:
        db_user = get_user_by_email(db, user_data.email)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email уже зарегистрирован"
            )

    # Проверяем, что username не занят другим пользователем
    if user_data.username and user_data.username != existing_user.username:
        db_user = get_user_by_username(db, user_data.username)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Имя пользователя уже занято"
            )

    # Обновляем пользователя
    updated_user = update_user(
        db,
        user_id,
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        notes=user_data.notes,
        is_active=user_data.is_active,
        role=user_data.role
    )

    return updated_user


@router.put("/users/{user_id}/password", status_code=status.HTTP_200_OK)
async def admin_change_password(
        user_id: int,
        password_data: UserPasswordChange,
        db: Session = Depends(get_db),
        _: User = Depends(get_current_admin_user)
):
    """Изменить пароль пользователя (только для администраторов)"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    change_user_password(db, user_id, password_data.new_password)

    return {"message": "Пароль успешно изменен"}


# Дополнительные эндпоинты для суперадминистраторов (если нужны)
@router.post("/superadmin/users", response_model=UserResponse)
async def superadmin_create_user(
        user_data: UserCreate,
        db: Session = Depends(get_db),
        current_superadmin: User = Depends(get_current_superadmin_user)
):
    """Создание нового пользователя (только для суперадминистраторов)"""
    # Проверяем, что email не занят
    db_user = get_user_by_email(db, user_data.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email уже зарегистрирован"
        )

    # Проверяем, что username не занят
    db_user = get_user_by_username(db, user_data.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя пользователя уже занято"
        )

    # Создаем пользователя (суперадмин может создавать пользователей с любой ролью)
    return create_user(
        db=db,
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        full_name=user_data.full_name,
        notes=user_data.notes,
        role=user_data.role,
        created_by=current_superadmin.id
    )