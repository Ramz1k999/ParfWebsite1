# app/crud/user.py
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from typing import Optional, List


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Получить пользователя по email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Получить пользователя по имени пользователя"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Получить пользователя по ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Получить список всех пользователей с пагинацией"""
    return db.query(User).offset(skip).limit(limit).all()


def create_user(
        db: Session,
        email: str,
        username: str,
        password: str,
        full_name: str,
        notes: Optional[str] = None,
        role: UserRole = UserRole.USER,
        created_by: Optional[int] = None
) -> User:
    """Создать нового пользователя"""
    hashed_password, salt = User.get_password_hash(password)
    db_user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        salt=salt,
        full_name=full_name,
        notes=notes,
        role=role,
        created_by=created_by
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(
        db: Session,
        user_id: int,
        email: Optional[str] = None,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        notes: Optional[str] = None,
        is_active: Optional[bool] = None,
        role: Optional[UserRole] = None
) -> Optional[User]:
    """Обновить данные пользователя"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    if email is not None:
        user.email = email
    if username is not None:
        user.username = username
    if full_name is not None:
        user.full_name = full_name
    if notes is not None:
        user.notes = notes
    if is_active is not None:
        user.is_active = is_active
    if role is not None:
        user.role = role

    db.commit()
    db.refresh(user)
    return user


def change_user_password(db: Session, user_id: int, new_password: str) -> Optional[User]:
    """Изменить пароль пользователя"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    hashed_password, salt = User.get_password_hash(new_password)
    user.hashed_password = hashed_password
    user.salt = salt

    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Аутентифицировать пользователя по email и паролю"""
    user = get_user_by_email(db, email)
    if not user:
        return None

    if not User.verify_password(password, user.hashed_password, user.salt):
        return None

    return user


def count_users(db: Session) -> int:
    """Получить общее количество пользователей"""
    return db.query(User).count()