# app/cache.py
from functools import wraps
import json
from typing import Any, Callable, Dict, Optional, TypeVar
import time

# Простая реализация кэша в памяти
cache_store: Dict[str, Dict[str, Any]] = {}

T = TypeVar('T')


def cache(ttl_seconds: int = 300):
    """
    Декоратор для кэширования результатов функции.

    Args:
        ttl_seconds: Время жизни кэша в секундах

    Returns:
        Декорированная функция
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Создаем ключ кэша на основе имени функции и аргументов
            key_parts = [func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(key_parts)

            # Проверяем, есть ли результат в кэше и не истек ли он
            if cache_key in cache_store:
                entry = cache_store[cache_key]
                if entry["expires"] > time.time():
                    return entry["data"]

            # Если результата нет в кэше или он истек, вызываем функцию
            result = func(*args, **kwargs)

            # Сохраняем результат в кэше
            cache_store[cache_key] = {
                "data": result,
                "expires": time.time() + ttl_seconds
            }

            return result

        return wrapper

    return decorator


def clear_cache(prefix: Optional[str] = None) -> None:
    """
    Очищает кэш.

    Args:
        prefix: Если указан, очищает только записи, начинающиеся с prefix
    """
    global cache_store
    if prefix:
        cache_store = {k: v for k, v in cache_store.items() if not k.startswith(prefix)}
    else:
        cache_store = {}