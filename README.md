# MediaTrack

Трекер фільмів, серіалів та ігор. Навчальний проєкт групи ТК-42.

Стек: фронт React + TypeScript + Vite, бек Python + FastAPI, база PostgreSQL (Neon).

## Структура

```
mediatrack/
├── backend/     # FastAPI
├── frontend/    # React + Vite
├── docs/
└── .github/
```

## Налаштування

Скопіювати `.env.example` у `.env` і прописати `DATABASE_URL`, `TMDB_API_KEY`, `RAWG_API_KEY`.
Справжні ключі в репо не комітимо.

```sh
cp .env.example .env
```

## Бекенд

```sh
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Перевірка: `GET http://localhost:8000/api/health` → `{"status":"ok"}`.
Тести: `pytest`.

## Фронтенд

```sh
cd frontend
npm install
npm run dev
```

Відкриється на `http://localhost:5173`.

## Правила

- Гілки: `feature/SCRUM-<номер>-<коротко>`.
- Коміти починаються з ключа Jira: `SCRUM-15 Короткий опис`.
- У `main` тільки через PR з одним апрувом і зеленим CI.
