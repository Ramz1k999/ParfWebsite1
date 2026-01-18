from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from app.routers import products, admin, cart, order, auth, admin_users, admin_orders, admin_currency
from app.middleware import log_requests_middleware
from app.exceptions import http_exception_handler
from app.logger import app_logger
from app.config import settings

# --- Список разрешённых фронт-доменов ---
origins = [
    "https://src-tjpz.onrender.com",
    "http://localhost:3000",
]

# --- Создание FastAPI ---
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

app_logger.info("Запуск API сервера")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# --- Middleware логирования запросов ---
app.middleware("http")(log_requests_middleware)

# --- Обработчики исключений ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):

    headers = {
        "Access-Control-Allow-Origin": ", ".join(origins),
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }

    exc_str = ""
    for err in exc.errors():
        loc = "->".join([str(l) for l in err["loc"]])
        exc_str += f"{err['msg']} for input `{err.get('input', None)}` in the field {loc}. "

    return JSONResponse(
        content=jsonable_encoder({
            "status_code": 422,
            "message": exc_str,
            "exception": "HTTP_422_UNPROCESSABLE_ENTITY"
        }),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        headers=headers
    )

app.add_exception_handler(HTTPException, http_exception_handler)

# --- Подключение роутеров ---
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(products.router, prefix="/api", tags=["products"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(admin_users.router, prefix="/api/admin", tags=["admin_users"])
app.include_router(admin_orders.router, prefix="/api/admin", tags=["admin_orders"])
app.include_router(cart.router, prefix="/api", tags=["cart"])
app.include_router(order.router, prefix="/api", tags=["orders"])
app.include_router(admin_currency.router, prefix="/api/admin", tags=["admin_currency"])

# --- Корневой эндпоинт ---
@app.get("/")
async def root():
    return {
        "message": "Perfume Store API",
        "version": settings.APP_VERSION,
        "docs": "/api/docs"
    }

# --- Health Check ---
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "api_version": settings.APP_VERSION
    }

# --- Shutdown Event ---
@app.on_event("shutdown")
def shutdown_event():
    app_logger.info("Завершение работы API сервера")

# --- Запуск через uvicorn ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
