from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from app.routers import products, admin, cart, order, auth, admin_users, admin_orders, admin_currency
from app.middleware import log_requests_middleware
from app.logger import app_logger
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# --- CORS middleware (централизованно для всех роутеров) ---
origins = ["https://src-tjpz.onrender.com", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, OPTIONS, PUT, DELETE
    allow_headers=["*"],
)

# --- Логирование запросов ---
app.middleware("http")(log_requests_middleware)

# --- Обработчики исключений ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Возвращаем JSON с описанием ошибок
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

app.add_exception_handler(HTTPException, lambda request, exc: JSONResponse(
    status_code=exc.status_code,
    content={"detail": exc.detail}
))

# --- Подключение роутеров ---
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
    return {"message": "Perfume Store API", "version": settings.APP_VERSION, "docs": "/api/docs"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "api_version": settings.APP_VERSION}
