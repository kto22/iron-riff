"""Работа с PostgreSQL: подключение, схема, начальные данные."""
import json
import time
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    brand       TEXT NOT NULL,
    model       TEXT NOT NULL,
    category    TEXT NOT NULL,
    price       NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    stock       INTEGER NOT NULL CHECK (stock >= 0),
    color       TEXT NOT NULL DEFAULT '#c0c0c0',
    description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS orders (
    id            SERIAL PRIMARY KEY,
    customer_name TEXT NOT NULL,
    email         TEXT NOT NULL,
    phone         TEXT NOT NULL,
    total         NUMERIC(12,2) NOT NULL,
    status        TEXT NOT NULL DEFAULT 'new',
    created_at    TIMESTAMP NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS order_items (
    id         SERIAL PRIMARY KEY,
    order_id   INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    title      TEXT NOT NULL,
    qty        INTEGER NOT NULL,
    price      NUMERIC(10,2) NOT NULL
);
"""

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "products.json"


class Database:
    def __init__(self, url: str):
        self.url = url

    @contextmanager
    def connect(self):
        """Соединение с автоматическим commit/rollback."""
        with psycopg.connect(self.url, row_factory=dict_row) as conn:
            yield conn

    def wait_ready(self, attempts: int = 30, delay: float = 2.0) -> None:
        """В k8s база может подняться позже приложения — ждём её."""
        for i in range(1, attempts + 1):
            try:
                with self.connect() as conn:
                    conn.execute("SELECT 1")
                return
            except psycopg.OperationalError as e:
                print(f"[db] попытка {i}/{attempts}: база недоступна ({e.__class__.__name__})")
                time.sleep(delay)
        raise RuntimeError("Не удалось подключиться к PostgreSQL")

    def init(self) -> None:
        """Создаёт таблицы и заполняет каталог из JSON, если он пуст."""
        with self.connect() as conn:
            # В PostgreSQL 15+ в схеме public нельзя создавать таблицы обычному
            # пользователю, поэтому заводим личную схему (search_path: "$user", public)
            conn.execute("CREATE SCHEMA IF NOT EXISTS AUTHORIZATION CURRENT_USER")
            conn.execute(SCHEMA)
            count = conn.execute("SELECT count(*) AS n FROM products").fetchone()["n"]
            if count == 0:
                products = json.loads(SEED_FILE.read_text(encoding="utf-8"))
                with conn.cursor() as cur:
                    cur.executemany(
                        "INSERT INTO products (brand, model, category, price, stock, color, description) "
                        "VALUES (%(brand)s, %(model)s, %(category)s, %(price)s, %(stock)s, %(color)s, %(description)s)",
                        products,
                    )
                print(f"[db] загружено товаров: {len(products)}")
