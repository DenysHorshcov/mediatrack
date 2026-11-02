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

Для майбутніх підключень БД і каталогів скопіювати `.env.example` у `.env` у корені репозиторію й заповнити потрібні значення локально. Справжні ключі в репо не комітимо.

```sh
cp .env.example .env
```

У PowerShell: `Copy-Item .env.example .env`. Поточний каркас ще не завантажує `.env`; для `/api/health`, Swagger і тесту ключі та БД не потрібні. Завантаження конфігурації буде додано на етапі підключення БД.

## Бекенд

Python 3.14, менеджер залежностей [uv](https://docs.astral.sh/uv/getting-started/installation/). Використовуємо uv 0.13.0, зафіксований у `backend/pyproject.toml`; перевірка встановленої версії — `uv --version`.

Команди однакові для PowerShell і Unix shell:

```sh
cd backend
uv python install
uv sync --locked
uv run --locked uvicorn app.main:app --reload
```

`uv python install` установлює Python за `backend/.python-version`. `uv sync --locked` створює `backend/.venv` і встановлює залежності, включно з групою `dev`, за `uv.lock`; невідповідність lock-файлу конфігурації спричиняє помилку. Активувати середовище вручну не потрібно: `uv run` використовує його сам.

- Перевірка: `GET http://localhost:8000/api/health` → `{"status":"ok"}`.
- Swagger: `http://localhost:8000/docs`.
- OpenAPI: `http://localhost:8000/openapi.json`.
- Тести з каталогу `backend`: `uv run --locked pytest -q`.

Залежності додаємо через `uv add <package>`, залежності розробки — `uv add --dev <package>`. У Git зберігаємо `pyproject.toml`, `uv.lock` і `.python-version`; `.venv` ігнорується. `httpx` поки належить до `dev` для TestClient; перед серверною інтеграцією каталогів його буде перенесено до runtime.

Структура бекенду:

```text
backend/
├── app/             # FastAPI-застосунок; точка входу app.main:app
├── tests/           # автоматизовані перевірки бекенду
├── .python-version  # версія Python для локального запуску та CI
├── pyproject.toml   # залежності й налаштування інструментів
└── uv.lock          # точні версії залежностей
```

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
