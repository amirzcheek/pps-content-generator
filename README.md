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

## Архитектура

| Файл | Назначение |
|------|------------|
| `templates.json` | Библиотека промптов (редактируется методистами) |
| `generator.py` | Ядро: загрузка шаблонов, сборка промптов, выбор модели, вызов API |
| `app.py` | HTTP-API на FastAPI поверх ядра |
| `frontend/` | Веб-интерфейс: Vite + React + react-router-dom (для портала ai.knus.edu.kz) |

### Маршрутизация по языку

| `language` | Модель |
|-----------|--------|
| `kk` | KazLLM-8B / Sherkala-8B (`KAZ_*`) |
| `ru`, `en` | Qwen3-14B через OVMS (`LLM_*`) |

Адреса и имена моделей задаются **только** через переменные окружения.

## Установка

Рекомендуется ставить зависимости в **виртуальное окружение** — оно изолирует
библиотеки проекта от системного Python и не требует прав на запись в глобальный
каталог. Создаётся один раз.

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

После активации в начале строки терминала появляется `(.venv)`. Все команды ниже
(`uvicorn`, `python generator.py`) выполняются внутри активированного окружения.
Выйти из него — командой `deactivate`.

Каталог `.venv/` уже добавлен в `.gitignore` и не попадает в репозиторий.

> Без виртуального окружения можно поставить зависимости и глобально
> (`pip install -r requirements.txt`), но на Windows это иногда упирается в
> блокировку файлов в `Scripts\` — venv эту проблему снимает.

## Переменные окружения

```bash
# Qwen3 (OVMS) — для русского и английского
export LLM_BASE_URL="http://qwen-ovms:8000/v3"
export LLM_MODEL="Qwen3-14B"
export LLM_API_KEY="not-needed"        # локальным моделям ключ обычно не нужен

# KazLLM / Sherkala — для казахского
export KAZ_BASE_URL="http://kazllm:8000/v1"
export KAZ_MODEL="KazLLM-8B"
export KAZ_API_KEY="not-needed"

# CORS — домены веб-интерфейса, которым разрешены запросы из браузера.
# Несколько доменов — через запятую. По умолчанию: https://ai.knus.edu.kz
export CORS_ORIGINS="https://ai.knus.edu.kz"
```

В PowerShell (Windows):

```powershell
$env:LLM_BASE_URL = "http://qwen-ovms:8000/v1"
$env:LLM_MODEL    = "Qwen3-14B"
$env:KAZ_BASE_URL = "http://kazllm:8000/v1"
$env:KAZ_MODEL    = "KazLLM-8B"
```

## Запуск

```bash
uvicorn app:app --host 0.0.0.0 --port 8080
```

Документация Swagger доступна на `http://localhost:8080/docs`.

### Офлайн-проверка без модели

```bash
python3 generator.py
```

Печатает список шаблонов и пример собранного промпта — модель не вызывается.

## Веб-интерфейс

Каталог [`frontend/`](frontend/) — SPA на **Vite + React + react-router-dom**.
Маршруты:

- `/` — список типов контента (карточки), подгружается из `GET /templates`;
- `/generate/:templateId` — форма генератора: базовые поля + динамические поля
  `extra_params` выбранного типа, предпросмотр промпта и генерация.

Интерфейс предназначен для размещения на портале **ai.knus.edu.kz**.

### Адрес backend

Задаётся переменной `VITE_API_BASE` (см. `frontend/.env.example`):

- **пусто** — запросы идут на `/api` (прокси Vite в dev; reverse-proxy на проде —
  CORS тогда не нужен вовсе);
- либо полный адрес ядра, например `http://127.0.0.1:8080` (тогда домен фронтенда
  должен быть в `CORS_ORIGINS` бэкенда).

### Локальная разработка

```bash
# 1. backend (в корне проекта)
uvicorn app:app --port 8080

# 2. frontend (в каталоге frontend/)
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
