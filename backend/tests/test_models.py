"""Тесты доменных классов: запуск `python -m pytest tests` из папки backend."""
import pytest

from app.errors import OutOfStockError, ValidationError
from app.models import Cart, Product


def make(pid, price, stock):
    return Product(id=pid, brand="Test", model=str(pid), category="electric", price=price, stock=stock)


def test_cart_total():
    cart = Cart()
    cart.add(1, 2)
    cart.add(2)
    cart.add(1)
    assert cart.items == {1: 3, 2: 1}
    assert cart.total({1: make(1, 100, 5), 2: make(2, 50, 5)}) == 350


def test_cart_rejects_bad_qty():
    with pytest.raises(ValidationError):
        Cart().add(1, 0)


def test_out_of_stock():
    with pytest.raises(OutOfStockError):
        make(1, 100, 1).check_available(2)
