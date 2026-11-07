# MediaTrack

Потрібні uv 0.13.0 та Node.js 22.

## Налаштування

У корені репозиторію створити `.env`, якщо його ще немає:

```sh
cp .env.example .env
```

Заповнити `DATABASE_URL` підключенням до `development`, а `TEST_DATABASE_URL` — до `test`. Підключення отримати приватно у Даниїла.

## Бекенд і перевірка БД

З кореня репозиторію:

```sh
cd backend
uv python install
uv sync --locked
uv run --locked python -m app.check_db
uv run --locked alembic upgrade head
uv run --locked uvicorn app.main:app --reload
```

API: http://localhost:8000/api/health
Swagger: http://localhost:8000/docs

Демонстраційні дані (з `backend`; пароль для `demo_olena` та `demo_taras` вводиться приховано):

```sh
uv run --locked python -m app.seed
```

Оновити зображення схеми та DBML (з `backend`):

```sh
uv run --locked python -m app.export_schema
```

## Фронтенд

В окремому терміналі з кореня репозиторію:

```sh
cd frontend
npm ci
npm run dev
```

Відкрити http://localhost:5173.

## Перевірки

З каталогу `backend`:

```sh
uv run --locked python -m app.check_db --test
uv run --locked pytest -q
```

Інтеграційні перевірки на окремій БД з `TEST_DATABASE_URL`, відмінній від `DATABASE_URL`:

```sh
uv run --locked alembic -x database=test upgrade head
uv run --locked pytest -q --database-tests
```

## Деплой

Робоча версія: https://mediatrack-7isg.onrender.com (безкоштовний хостинг засинає без запитів, перший запит може тривати ~50 с)

Один сервіс: FastAPI віддає API під `/api` і зібраний фронтенд (`frontend/dist`) з того ж домену. Будь-який GET-шлях поза `/api` повертає `index.html`, щоб працювали посилання React Router. Невідомі `/api/...` повертають JSON 404.

### Docker локально

З кореня репозиторію:

```sh
docker build -t mediatrack .
docker run --rm -p 8000:8000 --env-file .env mediatrack
```

Відкрити http://localhost:8000. Під час старту контейнер виконує `alembic upgrade head`, потім запускає uvicorn на порту `$PORT` (типово 8000).

### Змінні середовища

| Змінна | Призначення |
| --- | --- |
| `DATABASE_URL` | PostgreSQL (Neon, гілка `production`, direct-підключення з `sslmode=require`) |
| `TMDB_API_KEY` | ключ TMDB для фільмів і серіалів |
| `JWT_SECRET` | власне випадкове значення, напр. `openssl rand -hex 32` |
| `SESSION_COOKIE_SECURE` | `true` на HTTPS-хостингу |
| `FRONTEND_ORIGIN` | адреса сайту, напр. `https://<service>.onrender.com` |
| `PORT` | задає Render; локально типово 8000 |

`RAWG_API_KEY` не потрібен: ігри беруться зі Steam Store API без ключа.

### Render + Neon

1. Neon: створити окрему гілку `production`, скопіювати **direct** (не pooled) рядок підключення з `sslmode=require`. Гілки `development` і `test` для продакшну не використовувати.
2. Render: New → Web Service → цей GitHub-репозиторій, runtime **Docker**, план Free, гілка `main`, Health Check Path `/api/health`, auto-deploy після проходження CI.
3. Додати змінні середовища з таблиці вище.
4. Після деплою: зареєструватися, знайти фільм і гру, додати в бібліотеку, перевірити статистику.

Міграції виконуються при старті контейнера, бо Pre-Deploy Command на Render доступна лише на платних планах.

> Безкоштовний сервіс Render засинає без трафіку, перший запит може тривати ~50 с. **Відкрийте сайт за кілька хвилин до демо.**
