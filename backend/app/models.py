"""Доменные классы (ООП): товар, корзина, заказ."""
from dataclasses import dataclass, asdict, field
from datetime import datetime

from .errors import OutOfStockError, ValidationError

# Словарь категорий: код -> название на русском
CATEGORIES = {
    "electric": "Электрогитары",
    "bass": "Бас-гитары",
    "acoustic": "Акустика",
    "amp": "Усилители",
    "pedal": "Педали эффектов",
}


@dataclass
class Product:
    id: int
    brand: str
    model: str
    category: str
    price: float
    stock: int
    color: str = "#c0c0c0"
    description: str = ""

    @property
    def title(self) -> str:
        return f"{self.brand} {self.model}"

    def check_available(self, qty: int) -> None:
        """Бросает исключение, если товара на складе меньше qty."""
        if qty > self.stock:
            raise OutOfStockError(f"«{self.title}»: на складе {self.stock} шт., запрошено {qty}")

    def to_dict(self) -> dict:
        data = asdict(self)
        data["title"] = self.title
        data["category_name"] = CATEGORIES.get(self.category, self.category)
        return data

    @classmethod
    def from_row(cls, row: dict) -> "Product":
        row = dict(row)
        row["price"] = float(row["price"])
        return cls(**row)


class Cart:
    """Корзина: словарь {product_id: количество}."""

    def __init__(self):
        self.items: dict[int, int] = {}

    def add(self, product_id: int, qty: int = 1) -> None:
        if qty <= 0:
            raise ValidationError("Количество должно быть больше нуля")
        self.items[product_id] = self.items.get(product_id, 0) + qty

    def remove(self, product_id: int) -> None:
        self.items.pop(product_id, None)

    def is_empty(self) -> bool:
        return not self.items

    def total(self, products: dict[int, Product]) -> float:
        return round(sum(products[pid].price * qty for pid, qty in self.items.items()), 2)


@dataclass
class Order:
    customer_name: str
    email: str
    phone: str
    total: float
    lines: list = field(default_factory=list)  # [{product_id, title, qty, price}]
    id: int | None = None
    created_at: datetime | None = None
    status: str = "new"

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.created_at:
            data["created_at"] = self.created_at.isoformat(timespec="seconds")
        return data
