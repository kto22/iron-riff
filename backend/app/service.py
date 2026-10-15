"""Бизнес-логика магазина."""
from .cache import RedisCache
from .database import Database
from .errors import NotFoundError, ValidationError
from .models import CATEGORIES, Cart, Order, Product

# Словарь допустимых сортировок: параметр запроса -> SQL
SORTS = {
    "price_asc": "price ASC",
    "price_desc": "price DESC",
    "name": "brand, model",
}


class ShopService:
    def __init__(self, db: Database, cache: RedisCache):
        self.db = db
        self.cache = cache

    # ---------- товары ----------
    def list_products(self, category: str | None = None, q: str | None = None,
                      sort: str = "name") -> list[dict]:
        if category and category not in CATEGORIES:
            raise ValidationError(f"Неизвестная категория: {category}")
        if sort not in SORTS:
            raise ValidationError(f"Неизвестная сортировка: {sort}")

        key = f"products:{category or 'all'}:{(q or '').lower()}:{sort}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        sql = "SELECT * FROM products WHERE 1=1"
        params: dict = {}
        if category:
            sql += " AND category = %(category)s"
            params["category"] = category
        if q:
            sql += " AND (brand ILIKE %(q)s OR model ILIKE %(q)s)"
            params["q"] = f"%{q}%"
        sql += f" ORDER BY {SORTS[sort]}"

        with self.db.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        result = [Product.from_row(r).to_dict() for r in rows]
        self.cache.set(key, result)
        return result

    def get_product(self, product_id: int) -> Product:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM products WHERE id = %s", (product_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Товар #{product_id} не найден")
        return Product.from_row(row)

    def create_product(self, data: dict) -> Product:
        if data["category"] not in CATEGORIES:
            raise ValidationError(f"Неизвестная категория: {data['category']}")
        with self.db.connect() as conn:
            row = conn.execute(
                "INSERT INTO products (brand, model, category, price, stock, color, description) "
                "VALUES (%(brand)s, %(model)s, %(category)s, %(price)s, %(stock)s, %(color)s, %(description)s) "
                "RETURNING *", data).fetchone()
        self.cache.clear("products:")
        return Product.from_row(row)

    def delete_product(self, product_id: int) -> None:
        with self.db.connect() as conn:
            used = conn.execute("SELECT 1 FROM order_items WHERE product_id = %s LIMIT 1",
                                (product_id,)).fetchone()
            if used:
                raise ValidationError("Товар уже есть в заказах — удалить нельзя, обнулите остаток")
            deleted = conn.execute("DELETE FROM products WHERE id = %s", (product_id,)).rowcount
        if not deleted:
            raise NotFoundError(f"Товар #{product_id} не найден")
        self.cache.clear("products:")

    # ---------- заказы ----------
    def create_order(self, customer: dict, items: list[dict]) -> Order:
        cart = Cart()
        for item in items:
            cart.add(item["product_id"], item["qty"])
        if cart.is_empty():
            raise ValidationError("Корзина пуста")

        # Одна транзакция: блокируем строки товаров, проверяем остатки, списываем
        with self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM products WHERE id = ANY(%s) FOR UPDATE",
                                (list(cart.items),)).fetchall()
            products = {r["id"]: Product.from_row(r) for r in rows}

            missing = set(cart.items) - set(products)
            if missing:
                raise NotFoundError(f"Товары не найдены: {sorted(missing)}")
            for pid, qty in cart.items.items():
                products[pid].check_available(qty)

            order = Order(customer_name=customer["name"], email=customer["email"],
                          phone=customer["phone"], total=cart.total(products))
            row = conn.execute(
                "INSERT INTO orders (customer_name, email, phone, total) VALUES (%s, %s, %s, %s) "
                "RETURNING id, created_at",
                (order.customer_name, order.email, order.phone, order.total)).fetchone()
            order.id, order.created_at = row["id"], row["created_at"]

            for pid, qty in cart.items.items():
                p = products[pid]
                conn.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (qty, pid))
                conn.execute(
                    "INSERT INTO order_items (order_id, product_id, title, qty, price) "
                    "VALUES (%s, %s, %s, %s, %s)", (order.id, pid, p.title, qty, p.price))
                order.lines.append({"product_id": pid, "title": p.title, "qty": qty, "price": p.price})

        self.cache.clear("products:")
        self.cache.clear("stats")
        return order

    def list_orders(self) -> list[dict]:
        with self.db.connect() as conn:
            orders = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 50").fetchall()
            lines = conn.execute("SELECT * FROM order_items").fetchall()
        by_order: dict[int, list] = {}
        for line in lines:
            by_order.setdefault(line["order_id"], []).append(
                {"product_id": line["product_id"], "title": line["title"],
                 "qty": line["qty"], "price": float(line["price"])})
        return [Order(customer_name=o["customer_name"], email=o["email"], phone=o["phone"],
                      total=float(o["total"]), id=o["id"], created_at=o["created_at"],
                      status=o["status"], lines=by_order.get(o["id"], [])).to_dict()
                for o in orders]

    # ---------- статистика ----------
    def stats(self) -> dict:
        cached = self.cache.get("stats")
        if cached is not None:
            return cached
        with self.db.connect() as conn:
            stock = conn.execute(
                "SELECT category, sum(stock) AS units, sum(stock * price) AS value "
                "FROM products GROUP BY category").fetchall()
            sales = conn.execute(
                "SELECT p.category, sum(i.qty) AS units, sum(i.qty * i.price) AS revenue "
                "FROM order_items i JOIN products p ON p.id = i.product_id GROUP BY p.category").fetchall()
            orders = conn.execute("SELECT count(*) AS n, coalesce(sum(total),0) AS s FROM orders").fetchone()

        # Словарь категория -> показатели; заполняем нулями все категории
        by_cat = {code: {"name": name, "stock_units": 0, "stock_value": 0.0,
                         "sold_units": 0, "revenue": 0.0}
                  for code, name in CATEGORIES.items()}
        for r in stock:
            if r["category"] in by_cat:
                by_cat[r["category"]].update(stock_units=int(r["units"]), stock_value=float(r["value"]))
        for r in sales:
            if r["category"] in by_cat:
                by_cat[r["category"]].update(sold_units=int(r["units"]), revenue=float(r["revenue"]))

        result = {"categories": by_cat, "orders_count": orders["n"], "revenue_total": float(orders["s"])}
        self.cache.set("stats", result)
        return result
