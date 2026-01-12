# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from sqlalchemy.sql import func
from app.database import Base
import hashlib
import os
import enum


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class User(Base):
    """
    Модель пользователя в системе.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    salt = Column(String)  # Соль для хеширования пароля
    full_name = Column(String)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(Enum(UserRole), default=UserRole.USER)  # Заменяем is_admin на role
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def is_admin(self):
        """Проверка, является ли пользователь админом или суперадмином"""
        return self.role in (UserRole.ADMIN, UserRole.SUPERADMIN)

    @property
    def is_superadmin(self):
        """Проверка, является ли пользователь суперадмином"""
        return self.role == UserRole.SUPERADMIN

    @staticmethod
    def get_password_hash(password):
        """
        Создает хеш пароля с использованием SHA256 и случайной соли.

        Args:
            password: Пароль в открытом виде

        Returns:
            Кортеж (хешированный пароль, соль)
        """
        # Генерируем случайную соль
        salt = os.urandom(32).hex()

        # Создаем хеш с солью
        hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

        return hashed, salt

    @staticmethod
    def verify_password(plain_password, hashed_password, salt):
        """
        Проверяет соответствие пароля хешу.

        Args:
            plain_password: Пароль в открытом виде
            hashed_password: Хешированный пароль
            salt: Соль, использованная при хешировании

        Returns:
            True если пароль соответствует хешу, иначе False
        """
        # Создаем хеш с той же солью
        hashed = hashlib.sha256((plain_password + salt).encode('utf-8')).hexdigest()

        # Сравниваем хеши
        return hashed == hashed_password

    def __repr__(self):
        """Строковое представление объекта пользователя"""
        return f"<User {self.username} ({self.email})>"