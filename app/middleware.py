# app/middleware.py
from fastapi import Request
import time
from app.logger import api_logger


async def log_requests_middleware(request: Request, call_next):
    """Middleware для логирования запросов и времени их выполнения"""
    start_time = time.time()

    # Логируем начало запроса
    api_logger.info(f"Начало запроса: {request.method} {request.url.path}")

    # Выполняем запрос
    response = await call_next(request)

    # Вычисляем время выполнения
    process_time = time.time() - start_time

    # Логируем завершение запроса
    api_logger.info(
        f"Завершение запроса: {request.method} {request.url.path} "
        f"- Статус: {response.status_code} - Время: {process_time:.4f}s"
    )

    return response