# Образ агента: единый сервис — FastAPI отдаёт и API, и собранный React.
# Контекст сборки — корень репозитория.

# ── Стадия 1: сборка React-фронтенда ──
FROM node:20-slim AS frontend
WORKDIR /fe

# Префикс под-пути на портале и базовый адрес API (тот же префикс) —
# задаются аргументами сборки (см. docker-compose.yml). Vite подхватывает
# VITE_*-переменные из окружения.
ARG VITE_BASE=/agents/course-dev-content-generator/
ARG VITE_API_BASE=/agents/course-dev-content-generator
ENV VITE_BASE=$VITE_BASE \
    VITE_API_BASE=$VITE_API_BASE

COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Стадия 2: бэкенд + статика ──
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Зависимости (слой кешируется, пока requirements.txt не меняется).
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Код ядра (app.py, generator.py, templates.json).
COPY backend/ ./

# Собранный фронтенд кладём в каталог, который отдаёт FastAPI.
COPY --from=frontend /fe/dist ./static
ENV FRONTEND_DIST=/app/static

EXPOSE 8080

# Наружу порт пробрасывается только во внутреннюю сеть (см. docker-compose.yml),
# доступ снаружи — через nginx основного домена под /agents/<slug>/.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
