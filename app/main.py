from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from app.routers import products, admin, cart, order, auth, admin_users, admin_orders, admin_currency
from app.middleware import log_requests_middleware
from app.exceptions import validation_exception_handler, http_exception_handler
from app.logger import app_logger
from app.config import settings

# Создание экземпляра FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    API для интернет-магазина парфюмерии.

    ## Основные возможности:

    * **Товары**: Просмотр списка товаров, поиск, фильтрация
    * **Корзина**: Добавление товаров, изменение количества, удаление
    * **Заказы**: Оформление заказов, просмотр истории
    * **Аутентификация**: Вход в систему для администраторов
    * **Администрирование**: Управление товарами, заказами и пользователями
    """,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Логируем запуск приложения
app_logger.info("Запуск API сервера")

# CORS middleware для обработки запросов с разных доменов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://src-tjpz.onrender.com"],  # Добавлен порт 3001
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Добавляем middleware для логирования запросов
app.middleware("http")(log_requests_middleware)

# Добавляем обработчики исключений
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# Подключение роутеров
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(products.router, prefix="/api", tags=["products"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(admin_users.router, prefix="/api/admin", tags=["admin_users"])
app.include_router(admin_orders.router, prefix="/api/admin", tags=["admin_orders"])
app.include_router(cart.router, prefix="/api", tags=["cart"])
app.include_router(order.router, prefix="/api", tags=["orders"])
app.include_router(admin_currency.router, prefix="/api/admin", tags=["admin_currency"])


@app.get("/")
async def root():
    """
    Корневой эндпоинт, возвращает приветственное сообщение.
    """
    return {
        "message": "Perfume Store API",
        "version": settings.APP_VERSION,
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """
    Эндпоинт для проверки работоспособности API.
    Используется для мониторинга и проверок доступности.
    """
    return {
        "status": "healthy",
        "api_version": settings.APP_VERSION
    }


# Обработчик события завершения работы
@app.on_event("shutdown")
def shutdown_event():
    """
    Выполняется при завершении работы приложения.
    """
    app_logger.info("Завершение работы API сервера")


# Для запуска через uvicorn напрямую из файла
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)