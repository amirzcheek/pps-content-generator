# Генератор учебного контента для ППС

Интерфейс-независимое **ядро** для генерации учебных материалов на базе
локальных моделей вуза. Сервис не привязан к интерфейсу: к нему одинаково
подключаются веб-интерфейс портала **ai.knus.edu.kz**, Telegram-бот или n8n.

Главная ценность — **библиотека промптов** в [`templates.json`](templates.json).
Методисты правят формулировки прямо в JSON, без программирования. Качество вывода
определяется шаблонами, а не моделью.

## Типы контента (8)

1. Тест с вариантами ответов
2. Открытые вопросы
3. Практические задачи
4. Учебный кейс
5. План занятия
6. Рубрика оценивания
7. Учебный конспект
8. Глоссарий

## Структура проекта

```
content_generator/
├── backend/                 # HTTP-ядро (FastAPI + локальные модели)
│   ├── app.py               #   HTTP-API поверх ядра
│   ├── generator.py         #   ядро: шаблоны, сборка промптов, выбор модели, вызов API
│   ├── templates.json       #   библиотека промптов (редактируется методистами)
│   └── requirements.txt
├── frontend/                # веб-интерфейс (Vite + React + react-router-dom)
│   ├── src/
│   ├── package.json
│   └── vite.config.js
└── README.md
```

| Компонент | Назначение |
|-----------|------------|
| `backend/templates.json` | Библиотека промптов (редактируется методистами) |
| `backend/generator.py` | Ядро: загрузка шаблонов, сборка промптов, выбор модели, вызов API |
| `backend/app.py` | HTTP-API на FastAPI поверх ядра |
| `frontend/` | Веб-интерфейс: Vite + React + react-router-dom (для портала ai.knus.edu.kz) |

### Модели и резервирование

Основная — **локальная** модель; **резервная** — облачная **Gemini**
(`gemini-3.1-flash-lite`). Если локальная недоступна, генерация автоматически
переключается на Gemini. Для ресёрч-запросов можно сразу брать Gemini
(`prefer_fallback: true` в `POST /generate`).

| Назначение | Переменные | Когда используется |
|-----------|-----------|--------------------|
| Основная (локальная), ru/en | `LLM_*` | в первую очередь |
| Казахский | `KAZ_*` (или `LLM_*`, если пусто) | для `kk` |
| Резервная (Gemini) | `FALLBACK_*` | если основная недоступна / `prefer_fallback` |

Адреса и ключи — **только** через переменные окружения. Имя модели **всегда
передаётся явно** (иначе шлюз берёт дорогую по умолчанию); резервная по умолчанию —
`gemini-3.1-flash-lite`. Ответ `/generate` содержит поле `source` —
`основная` или `резервная`.

## Установка

Рекомендуется ставить зависимости в **виртуальное окружение** — оно изолирует
библиотеки проекта от системного Python и не требует прав на запись в глобальный
каталог. Создаётся один раз.

**Linux / macOS:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

После активации в начале строки терминала появляется `(.venv)`. Все команды ниже
(`uvicorn`, `python generator.py`) выполняются из каталога `backend/` внутри
активированного окружения. Выйти из него — командой `deactivate`.

Каталог `.venv/` уже добавлен в `.gitignore` и не попадает в репозиторий.

> Без виртуального окружения можно поставить зависимости и глобально
> (`pip install -r requirements.txt`), но на Windows это иногда упирается в
> блокировку файлов в `Scripts\` — venv эту проблему снимает.

## Переменные окружения

```bash
# Основная (локальная) модель — OVMS/Qwen3 (путь /v3!). Пусто -> всё на Gemini.
export LLM_BASE_URL="http://<LLM_HOST>:8000/v3"
export LLM_MODEL="OpenVINO/Qwen3-14B-int8-ov"   # передаётся явно
export LLM_API_KEY="not-needed"                 # OVMS без авторизации
export LLM_TIMEOUT="300"                         # CPU-инференс медленный
export LLM_DISABLE_THINKING="true"               # отключить <think> у Qwen3

# Казахский (необязательно) — отдельный эндпоинт; пусто -> как LLM_*/резерв.
export KAZ_BASE_URL=""
export KAZ_MODEL=""
export KAZ_API_KEY=""

# Резервная (облачная) модель — Gemini.
export FALLBACK_BASE_URL="https://<gemini-шлюз>/v1"
export FALLBACK_MODEL="gemini-3.1-flash-lite"
export FALLBACK_API_KEY="<ключ>"

# CORS — домены веб-интерфейса, которым разрешены запросы из браузера.
export CORS_ORIGINS="https://ai.knus.edu.kz"
```

В PowerShell (Windows):

```powershell
$env:LLM_BASE_URL      = "http://<LLM_HOST>:8000/v3"
$env:LLM_MODEL         = "OpenVINO/Qwen3-14B-int8-ov"
$env:LLM_TIMEOUT       = "300"
$env:FALLBACK_BASE_URL = "https://<gemini-шлюз>/v1"
$env:FALLBACK_MODEL    = "gemini-3.1-flash-lite"
$env:FALLBACK_API_KEY  = "<ключ>"
```

### Эндпоинты генерации

| Метод | Назначение |
|-------|-----------|
| `POST /generate` | разовый ответ JSON (для n8n и простых клиентов) |
| `POST /generate/stream` | потоковая отдача (SSE) — текст идёт по мере генерации, использует веб-интерфейс |

Оба отключают размышления Qwen3 (`enable_thinking=false`) и уважают `LLM_TIMEOUT`.

## Запуск

```bash
cd backend
uvicorn app:app --host 0.0.0.0 --port 8080
```

Документация Swagger доступна на `http://localhost:8080/docs`.

### Офлайн-проверка без модели

```bash
cd backend
python3 generator.py
```

Печатает список шаблонов и пример собранного промпта — модель не вызывается.

## Веб-интерфейс

Каталог [`frontend/`](frontend/) — SPA на **Vite + React + react-router-dom**.
Маршруты:

- `/` — список типов контента (карточки), подгружается из `GET /templates`;
- `/generate/:templateId` — форма генератора: базовые поля + динамические поля
  `extra_params` выбранного типа, предпросмотр промпта и генерация.

Интерфейс предназначен для размещения на портале **ai.knus.edu.kz** и оформлен
в его стиле (шрифт DM Sans, палитра и токены портала).

### Интеграция с порталом (навбар, язык, роли)

Навбар повторяет topbar портала и адаптирован под этого агента:

- бренд **KNUS Digital** ведёт на портал, рядом — название агента (ссылка на
  главную приложения);
- переключатель языка **RU / KZ / EN** — задаёт язык интерфейса и язык генерации
  (хранится в `localStorage` под общим с порталом ключом `coursehub_lang`);
- имя пользователя, кнопка **«Выйти»** (на `…/api/auth/logout` портала);
- ссылка **«Админка»** — **видна только администраторам**.

Роль и имя берутся из сессии портала: фронтенд запрашивает `GET /api/auth/session`
(`{ user: { displayName, isAdmin } }`) через серверный прокси. Логика вынесена в
хук [`src/auth/useSession.js`](frontend/src/auth/useSession.js) — это точка
подключения существующего входа платформы / Azure AD SSO. Пока SSO не подключён,
хук делает graceful fallback на «гостя» (без админки). Для превью админ-вида
локально задайте `VITE_PREVIEW_ADMIN=true`.

Переменные интеграции (см. `frontend/.env.example`):

| Переменная | Назначение |
|-----------|------------|
| `VITE_PORTAL_URL` | Базовый URL портала (бренд, выход, админка). По умолчанию `https://ai.knus.edu.kz` |
| `VITE_PREVIEW_ADMIN` | `true` — показать «Админку» локально, пока нет сессии портала |

### Адрес backend

Задаётся переменной `VITE_API_BASE` (см. `frontend/.env.example`):

- **пусто** — запросы идут на `/api` (прокси Vite в dev; reverse-proxy на проде —
  CORS тогда не нужен вовсе);
- либо полный адрес ядра, например `http://127.0.0.1:8080` (тогда домен фронтенда
  должен быть в `CORS_ORIGINS` бэкенда).

### Локальная разработка

```bash
# 1. backend
cd backend
uvicorn app:app --port 8080

# 2. frontend (в отдельном терминале)
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Dev-сервер Vite проксирует `/api/*` на backend (`vite.config.js`), поэтому при
локальной разработке CORS настраивать не нужно.

### Сборка для портала

```bash
cd frontend
npm run build      # статика в frontend/dist/
```

Содержимое `frontend/dist/` выкладывается на портал. Запросы к API проксируйте на
ядро тем же reverse-proxy под путём `/api` (тогда `VITE_API_BASE` оставьте пустым),
либо укажите полный адрес ядра в `VITE_API_BASE` и добавьте домен портала в
`CORS_ORIGINS` бэкенда.

## Примеры запросов

### Список типов контента

```bash
curl http://localhost:8080/templates
```

### Предпросмотр промпта (без вызова модели)

```bash
curl -X POST http://localhost:8080/preview \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "test_multiple_choice",
    "subject": "История Казахстана",
    "topic": "Образование Казахского ханства",
    "level": "бакалавриат",
    "language": "ru",
    "count": "5",
    "extra": "упор на причинно-следственные связи"
  }'
```

### Генерация

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "lesson_plan",
    "subject": "Физика",
    "topic": "Законы Ньютона",
    "level": "бакалавриат",
    "language": "ru",
    "format": "семинар",
    "duration": "90",
    "temperature": 0.7,
    "max_tokens": 2048
  }'
```

### Генерация на казахском (маршрутизация на KazLLM)

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "glossary",
    "subject": "Информатика",
    "topic": "Алгоритмдер",
    "language": "kk",
    "count": "10"
  }'
```

## Коды ответов

| Код | Значение |
|-----|----------|
| `200` | Успех |
| `400` | Неверные или недостающие параметры (нет `subject`/`topic`, неизвестный шаблон или язык) |
| `502` | Ошибка модели или сети (модель недоступна, таймаут) |

## Подключение фронтендов

Ядро остаётся неизменным — фронтенды обращаются к тем же HTTP-эндпоинтам.

### Telegram-бот

1. По старту бот запрашивает `GET /templates` и строит меню из типов контента.
2. Собирает у преподавателя `subject`, `topic`, `language` и нужные параметры
   шаблона (подсказки берёт из `extra_params`).
3. Отправляет `POST /generate` и присылает `content` пользователю.
   Для отладки шаблонов можно использовать `POST /preview`.

### Веб-интерфейс (портал ai.knus.edu.kz)

1. Форма подгружает типы из `GET /templates` (выпадающий список) и динамически
   показывает поля по `extra_params`.
2. Отправляет `POST /generate`, выводит `content`.
3. **CORS уже настроен** в `app.py`: домены фронтенда задаются переменной
   `CORS_ORIGINS` (по умолчанию `https://ai.knus.edu.kz`). Браузер портала
   обращается к API без дополнительной настройки. Для мониторинга есть
   `GET /health`.

### n8n

1. Нода **HTTP Request**: метод `POST`, URL `http://<host>:8080/generate`,
   тело — JSON с параметрами.
2. Результат (`content`) передаётся дальше по сценарию: сохранение в Google Docs,
   отправка в чат, рассылка и т.п.
3. `GET /templates` можно вызвать отдельной нодой, чтобы наполнить выбор типа.

## Примечания

- Весь расчёт — на локальные модели внутри сети вуза. Персональные данные не
  обрабатываются и не хранятся.
- Минимум зависимостей: `fastapi`, `uvicorn`, `openai`, `pydantic`.
- Чтобы добавить новый тип контента, достаточно дописать объект в `templates.json` —
  код менять не нужно.
