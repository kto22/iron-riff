"""FastAPI-приложение гитарного магазина IRON RIFF."""
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Header, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import config
from .cache import RedisCache
from .charts import stats_chart
from .database import Database
from .errors import AuthError, ShopError
from .models import CATEGORIES
from .service import ShopService

db = Database(config.DATABASE_URL)
cache = RedisCache(config.REDIS_SENTINEL_HOST, config.REDIS_SENTINEL_PORT,
                   config.REDIS_MASTER_NAME, config.CACHE_TTL)
shop = ShopService(db, cache)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.wait_ready()
    db.init()
    yield


app = FastAPI(title="IRON RIFF Guitar Shop", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json")
api = APIRouter(prefix="/api")


# ---------- схемы запросов (валидация pydantic) ----------
class Customer(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str = Field(min_length=5, max_length=20)


class OrderItem(BaseModel):
    product_id: int
    qty: int = Field(gt=0, le=10)


class OrderIn(BaseModel):
    customer: Customer
    items: list[OrderItem]


class ProductIn(BaseModel):
    brand: str = Field(min_length=1)
    model: str = Field(min_length=1)
    category: str
    price: float = Field(ge=0)
    stock: int = Field(ge=0)
    color: str = "#c0c0c0"
    description: str = ""


# ---------- обработка ошибок ----------
@app.exception_handler(ShopError)
async def shop_error_handler(request: Request, exc: ShopError):
    return JSONResponse(status_code=exc.status, content={"error": exc.message})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    print(f"[error] {request.url.path}: {exc!r}")
    return JSONResponse(status_code=500, content={"error": "Внутренняя ошибка сервера"})


def require_admin(token: str | None) -> None:
    if token != config.ADMIN_TOKEN:
        raise AuthError("Нужен правильный X-Admin-Token")


# ---------- эндпоинты ----------
@api.get("/health")
def health():
    return {"status": "ok", "redis": cache.ping()}


@api.get("/categories")
def categories():
    return CATEGORIES


@api.get("/products")
def products(category: str | None = None, q: str | None = None, sort: str = Query("name")):
    return shop.list_products(category, q, sort)


@api.get("/products/{product_id}")
def product(product_id: int):
    return shop.get_product(product_id).to_dict()


@api.post("/products", status_code=201)
def create_product(data: ProductIn, x_admin_token: str | None = Header(None)):
    require_admin(x_admin_token)
    return shop.create_product(data.model_dump()).to_dict()


@api.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, x_admin_token: str | None = Header(None)):
    require_admin(x_admin_token)
    shop.delete_product(product_id)


@api.post("/orders", status_code=201)
def create_order(data: OrderIn):
    order = shop.create_order(data.customer.model_dump(), [i.model_dump() for i in data.items])
    return order.to_dict()


@api.get("/orders")
def orders(x_admin_token: str | None = Header(None)):
    require_admin(x_admin_token)
    return shop.list_orders()


@api.get("/stats")
def stats():
    return shop.stats()


@api.get("/stats/chart.png")
def chart():
    return Response(content=stats_chart(shop.stats()), media_type="image/png")


app.include_router(api)
