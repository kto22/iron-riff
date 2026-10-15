# IRON RIFF — гитарный магазин

Учебный проект по Python: интернет-магазин гитар в стиле метал-постеров 80-х.

**Стек:** FastAPI · PostgreSQL (Crunchy Postgres Operator) · Redis Sentinel (кэш) · HTML/CSS/JS + nginx · matplotlib · MicroK8s.

## Структура

```
backend/            FastAPI-приложение
  app/
    main.py         эндпоинты, схемы pydantic, обработчики ошибок
    service.py      бизнес-логика (ShopService)
    models.py       классы Product, Cart, Order, словарь CATEGORIES
    database.py     PostgreSQL: схема, начальные данные
    cache.py        RedisCache через Sentinel (с graceful fallback)
    charts.py       график статистики в matplotlib
    errors.py       иерархия исключений ShopError
  data/products.json  файл с начальным каталогом
  tests/            pytest-тесты доменных классов
frontend/           статический сайт (index.html, style.css, app.js) + nginx
infra/
  k8s/              манифесты: namespace, PostgresCluster, Redis+Sentinel, backend, frontend, ingress
  scripts/install.sh  установка MicroK8s и всего стека на Ubuntu 24.04
  scripts/deploy.sh   деплой с ноутбука одной командой
  docker-compose.yml  локальный запуск без k8s
docs/               отчёт и презентация
```

## Требования курса

| Требование | Где |
|---|---|
| ООП | `Product`, `Cart`, `Order`, `ShopService`, `Database`, `RedisCache` |
| Словари | `CATEGORIES`, `SORTS`, корзина `{id: qty}`, статистика по категориям |
| Обработка ошибок | `errors.py`, `try/except` в `cache.py` и `database.py`, обработчики в `main.py` |
| Визуализация | сайт + график matplotlib `/api/stats/chart.png` |
| БД / файлы | PostgreSQL + `data/products.json` |

## API

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/products?category=&q=&sort=` | каталог (кэшируется в Redis) |
| GET | `/api/products/{id}` | товар |
| POST | `/api/products` | добавить товар (заголовок `X-Admin-Token`) |
| DELETE | `/api/products/{id}` | удалить товар (админ) |
| POST | `/api/orders` | оформить заказ |
| GET | `/api/orders` | список заказов (админ) |
| GET | `/api/stats`, `/api/stats/chart.png` | статистика и график |
| GET | `/api/docs` | Swagger UI |

## CI/CD

GitHub Actions (`.github/workflows/ci-cd.yml`):
1. **test** — `pytest` на каждый push и pull request;
2. **build** — сборка образов `shop-backend` и `shop-frontend` с тегом коммита, архив образов сохраняется как artifact;
3. **deploy** (только push в `main`) — загрузка образов на сервер по SSH (`ctr image import`),
   `kubectl apply` манифестов, ожидание rollout, удаление старых образов и проверка `/api/health`.

Секреты репозитория: `SERVER_HOST` — IP сервера, `SSH_KEY` — приватный SSH-ключ root.

## Запуск

Сервер: `bash infra/scripts/deploy.sh root@<ip>` с ноутбука (или `bash infra/scripts/install.sh` на сервере).
Локально: `docker compose -f infra/docker-compose.yml up --build` → http://localhost:8080.
Тесты: `cd backend && python -m pytest tests`.

Токен админки по умолчанию: `IronRiff-2026` (переменная `ADMIN_TOKEN` при установке).
