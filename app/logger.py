# app/logger.py (обновление)
import logging
import sys
from pathlib import Path
from app.config import settings

# Создаем директорию для логов, если она не существует
log_dir = Path(settings.LOG_DIR)
log_dir.mkdir(exist_ok=True)


# Настройка логгера
def setup_logger(name: str, log_file: str = None, level=None):
    """
    Настраивает логгер с указанным именем.

    Args:
        name: Имя логгера
        log_file: Путь к файлу логов (если None, логи выводятся только в консоль)
        level: Уровень логирования

    Returns:
        Настроенный логгер
    """
    if level is None:
        level = getattr(logging, settings.LOG_LEVEL)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Обработчик для записи в файл (если указан)
    if log_file:
        file_path = log_dir / log_file
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Создаем логгеры для разных компонентов
app_logger = setup_logger("app", "app.log")
api_logger = setup_logger("api", "api.log")
db_logger = setup_logger("db", "db.log")
auth_logger = setup_logger("auth", "auth.log")