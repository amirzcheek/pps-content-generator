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

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import generator

app = FastAPI(
    title="Генератор учебного контента для ППС",
    description="Интерфейс-независимое ядро генерации учебных материалов "
                "на базе локальных моделей вуза.",
    version="1.0.0",
)


class GenerateRequest(BaseModel):
    """Модель запроса на сборку промпта и генерацию.

    Обязательны template_id, subject, topic. Остальные параметры
    необязательны — для тех шаблонов, которые их используют."""

    template_id: str = Field(..., description="Идентификатор шаблона из /templates")
    subject: str = Field(..., description="Предмет / дисциплина")
    topic: str = Field(..., description="Тема")
    level: Optional[str] = Field("бакалавриат", description="Уровень обучения")
    language: str = Field("ru", description="Язык ответа: ru | kk | en")
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


def _to_params(req: GenerateRequest) -> dict:
    """Преобразует запрос в словарь параметров для ядра,
    отбрасывая служебные поля вызова модели."""
    params = req.model_dump()
    params.pop("temperature", None)
    params.pop("max_tokens", None)
    return params


@app.get("/templates")
def get_templates():
    """Список типов контента с подсказками по параметрам — для меню фронтенда."""
    return {"templates": generator.list_templates()}


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
        )
    except ValueError as exc:
        # Неверные параметры запроса.
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        # Ошибка модели или сети — внешняя зависимость недоступна.
        raise HTTPException(status_code=502, detail=str(exc))
    return result
