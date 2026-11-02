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
uv run --locked uvicorn app.main:app --reload
```

API: http://localhost:8000/api/health
Swagger: http://localhost:8000/docs

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
