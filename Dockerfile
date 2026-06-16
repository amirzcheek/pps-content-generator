# Образ сервиса генератора учебного контента.
# Контекст сборки — корень репозитория; код берётся из backend/.
FROM python:3.12-slim

# Не писать .pyc, не буферизовать stdout/stderr (логи сразу видны в docker logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала зависимости — слой кешируется, пока requirements.txt не меняется.
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Затем код ядра (app.py, generator.py, templates.json).
COPY backend/ ./

# Сервис слушает 8080 внутри контейнера.
EXPOSE 8080

# Запуск uvicorn. Наружу контейнера порт пробрасывается только на localhost
# (см. docker-compose.yml), доступ извне — через nginx.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
