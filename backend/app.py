# -*- coding: utf-8 -*-
"""
HTTP-сервис (FastAPI) поверх ядра генератора учебного контента.

Интерфейс-независимый API: к нему подключается любой фронтенд (Telegram-бот,
веб-форма, n8n) без изменения ядра generator.py.

Эндпоинты:
  - GET  /templates  — список типов контента для меню фронтенда.
  - POST /preview    — собрать промпт без вызова модели (отладка).
  - POST /generate   — полная генерация через локальную модель.
"""

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

import generator

app = FastAPI(
    title="Генератор учебного контента для ППС",
    description="Интерфейс-независимое ядро генерации учебных материалов "
                "на базе локальных моделей вуза.",
    version="1.0.0",
    # Префикс под-пути на портале (например /agents/course-dev-content-generator).
    # Нужен, чтобы Swagger/openapi отдавали корректные URL за reverse-proxy.
    # Пусто — если сервис в корне домена.
    root_path=os.getenv("ROOT_PATH", ""),
)

# CORS: веб-интерфейс на портале ai.knus.edu.kz обращается к API из браузера
# с другого домена. Список разрешённых источников задаётся через переменную
# окружения CORS_ORIGINS (домены через запятую), чтобы не хардкодить.
# По умолчанию — портал вуза.
_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "https://ai.knus.edu.kz",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins if origin.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    """Модель запроса на сборку промпта и генерацию.

    Обязательны template_id, subject, topic. Остальные параметры
    необязательны — для тех шаблонов, которые их используют."""

    template_id: str = Field(..., description="Идентификатор шаблона из /templates")
    subject: str = Field(..., description="Предмет / дисциплина")
    topic: str = Field(..., description="Тема")
    level: Optional[str] = Field("бакалавриат", description="Уровень обучения")
    # Язык интерфейса/генерации с фронтенда. Приоритетнее устаревшего language.
    lang: Optional[str] = Field(None, description="Язык вывода: ru | kk | en")
    language: str = Field("ru", description="Устар. синоним lang (для совместимости)")
    extra: Optional[str] = Field("", description="Свободные пожелания преподавателя")

    # Необязательные параметры конкретных шаблонов.
    count: Optional[str] = Field(None, description="Количество элементов")
    options: Optional[str] = Field(None, description="Кол-во вариантов ответа")
    difficulty: Optional[str] = Field(None, description="Сложность")
    depth: Optional[str] = Field(None, description="Глубина проработки")
    with_solutions: Optional[str] = Field(None, description="Прилагать решения")
    context: Optional[str] = Field(None, description="Контекст ситуации (кейс)")
    duration: Optional[str] = Field(None, description="Длительность занятия, мин")
    format: Optional[str] = Field(None, description="Формат занятия")
    work_type: Optional[str] = Field(None, description="Тип оцениваемой работы")
    scale: Optional[str] = Field(None, description="Шкала оценивания")
    length: Optional[str] = Field(None, description="Объём конспекта")

    # Параметры вызова модели (для /generate).
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Креативность")
    max_tokens: int = Field(2048, gt=0, le=8192, description="Лимит токенов ответа")
    prefer_fallback: bool = Field(
        False,
        description="Сразу использовать резервную модель Gemini "
                    "(например, для ресёрч-запросов). По умолчанию — локальная.",
    )


def _to_params(req: GenerateRequest) -> dict:
    """Преобразует запрос в словарь параметров для ядра,
    отбрасывая служебные поля вызова модели."""
    params = req.model_dump()
    params.pop("temperature", None)
    params.pop("max_tokens", None)
    params.pop("prefer_fallback", None)
    # Эффективный язык: lang (новое поле) -> language (старое) -> ru.
    lang = params.pop("lang", None)
    params["language"] = (lang or params.get("language") or "ru").strip().lower()
    return params


@app.get("/health")
def health():
    """Проверка живости сервиса — для мониторинга на портале."""
    return {"status": "ok"}


@app.get("/auth/session")
def auth_session(request: Request):
    """Текущий пользователь для навбара (имя + флаг админа).

    Авторизация выполняется платформой на уровне Caddy (forward_auth). После
    успешной проверки платформа может прокидывать заголовки с данными пользователя
    (через copy_headers в forward_auth). Здесь читаем распространённые варианты;
    если заголовков нет — возвращаем «гостя» (навбар просто не покажет имя/админку).

    Имена заголовков можно переопределить через AUTH_USER_HEADERS / AUTH_ADMIN_HEADER.
    """
    h = request.headers
    user_headers = (
        os.getenv("AUTH_USER_HEADERS")
        or "remote-name,x-forwarded-user,remote-user,x-auth-user,x-user-name"
    ).split(",")
    display_name = ""
    for name in user_headers:
        value = h.get(name.strip())
        if value:
            display_name = value
            break

    admin_header = os.getenv("AUTH_ADMIN_HEADER", "x-is-admin")
    groups = (h.get("remote-groups") or h.get("x-forwarded-groups") or "").lower()
    is_admin = h.get(admin_header, "").lower() in ("1", "true", "yes") or "admin" in groups

    return {"user": {"displayName": display_name, "isAdmin": is_admin}}


@app.get("/templates")
def get_templates(lang: str = "ru"):
    """Список типов контента с подсказками по параметрам — для меню фронтенда.
    Названия/описания/подсказки локализуются по ?lang=ru|kk|en."""
    return {"templates": generator.list_templates(lang)}


@app.post("/preview")
def preview(req: GenerateRequest):
    """Сборка промпта без вызова модели — для отладки шаблонов."""
    try:
        messages = generator.build_messages(req.template_id, _to_params(req))
    except ValueError as exc:
        # Неверные/недостающие параметры — ошибка клиента.
        raise HTTPException(status_code=400, detail=str(exc))
    return {"messages": messages}


@app.post("/generate")
def generate(req: GenerateRequest):
    """Полная генерация учебного материала через локальную модель."""
    try:
        result = generator.generate(
            req.template_id,
            _to_params(req),
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            prefer_fallback=req.prefer_fallback,
        )
    except ValueError as exc:
        # Неверные параметры запроса.
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        # Ошибка модели или сети — внешняя зависимость недоступна.
        raise HTTPException(status_code=502, detail=str(exc))
    return result


@app.post("/generate/stream")
def generate_stream(req: GenerateRequest):
    """Потоковая генерация (SSE): текст идёт в UI по мере поступления.

    Формат — text/event-stream. Каждое событие: `data: <json>` с полями
    type=meta|chunk|done|error (см. generator.stream_generate).
    """
    def event_source():
        for event in generator.stream_generate(
            req.template_id,
            _to_params(req),
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            prefer_fallback=req.prefer_fallback,
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Просим nginx не буферизовать поток (иначе текст придёт пачкой в конце).
            "X-Accel-Buffering": "no",
        },
    )


# ── Раздача собранного веб-интерфейса (React) ──
# Когда агент развёрнут как единый сервис под /agents/<slug>/, FastAPI отдаёт и
# API (выше), и статику собранного React-приложения. Каталог сборки задаётся
# переменной FRONTEND_DIST (по умолчанию backend/static, куда кладётся dist при
# сборке образа). Если каталога нет — сервис работает как чистый API.
#
# ВАЖНО: этот блок идёт ПОСЛЕ объявления API-маршрутов — поэтому /health,
# /templates, /preview, /generate (а также /docs, /openapi.json) имеют приоритет,
# а catch-all отдаёт SPA только на остальные GET-запросы.
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", str(Path(__file__).parent / "static")))

if FRONTEND_DIST.is_dir():
    _index_file = FRONTEND_DIST / "index.html"
    _dist_root = FRONTEND_DIST.resolve()

    # Ассеты и SPA отдаём через один catch-all (FileResponse), а не StaticFiles-mount:
    # mount несовместим с root_path при обрезании префикса на nginx, а обычный
    # маршрут — совместим. Content-Type подбирается по расширению автоматически.
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        """Любой прочий GET -> реальный файл из сборки (js/css/favicon),
        иначе index.html (клиентский роутинг react-router).
        Есть защита от выхода за пределы каталога сборки."""
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and _dist_root in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_index_file)
