# app/exceptions.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.logger import app_logger


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации запросов"""
    errors = []
    for error in exc.errors():
        error_msg = {
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        }
        errors.append(error_msg)

    app_logger.warning(f"Ошибка валидации: {errors}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors,
            "message": "Ошибка валидации данных"
        }
    )


async def http_exception_handler(request: Request, exc):
    """Обработчик HTTP исключений"""
    app_logger.warning(f"HTTP исключение: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "message": str(exc.detail)
        }
    )