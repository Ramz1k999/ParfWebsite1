import os
from pydantic import BaseSettings  # Изменено с pydantic_settings на pydantic


class Settings(BaseSettings):
    """
    Настройки приложения, загружаемые из переменных окружения.
    """
    # Настройки базы данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/perfume_store")

    # Настройки JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-should-be-at-least-32-characters")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 часа

    # Настройки приложения
    APP_NAME: str = "Perfume Store API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "API для интернет-магазина парфюмерии"

    # Настройки CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",  # React dev server (стандартный порт)
        "http://localhost:5000",  # Другой возможный порт
        "http://localhost:8080",  # Еще один возможный порт
        "http://127.0.0.1:3000",  # Через IP вместо localhost
        "http://127.0.0.1:5000",
        "http://127.0.0.1:8080",
        "http://localhost",  # Без указания порта
        "http://127.0.0.1",
        "https://src-tjpz.onrender.com",
        "https://parfwebsite1.onrender.com" # Продакшен URL (если есть)
    ]

    # Настройки логирования
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = "logs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Создаем экземпляр настроек
settings = Settings()