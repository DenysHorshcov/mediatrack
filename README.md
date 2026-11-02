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
