"""Собственная иерархия исключений магазина."""


class ShopError(Exception):
    """Базовая ошибка магазина. status — HTTP-код для ответа."""
    status = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(ShopError):
    status = 404


class OutOfStockError(ShopError):
    status = 409


class ValidationError(ShopError):
    status = 422


class AuthError(ShopError):
    status = 401
