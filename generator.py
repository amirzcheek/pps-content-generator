# -*- coding: utf-8 -*-
"""
Ядро генератора учебного контента для ППС (профессорско-преподавательского состава).

Сервис интерфейс-независимый: здесь только бизнес-логика — загрузка библиотеки
промптов, сборка сообщений для модели, выбор модели по языку и сам вызов
OpenAI-совместимого API. Любой фронтенд (Telegram-бот, веб-форма, n8n) подключается
к этому ядру через app.py без изменения кода.

Главная ценность — библиотека промптов в templates.json: методисты правят
формулировки прямо в JSON, без программирования.
"""

import os
import json
from pathlib import Path

# Путь к библиотеке промптов рядом с этим файлом.
TEMPLATES_PATH = Path(__file__).parent / "templates.json"

# Человекочитаемые названия языков для подстановки в системный промпт.
# Ключ — код языка из запроса, значение — как назвать язык модели.
LANGUAGE_NAMES = {
    "ru": "русском",
    "kk": "казахском",
    "en": "английском (English)",
}

# Значения по умолчанию для необязательных параметров шаблонов.
# Используются, если фронтенд не передал параметр явно.
DEFAULT_PARAMS = {
    "count": "10",
    "options": "4",
    "difficulty": "средняя",
    "depth": "стандартная",
    "with_solutions": "да",
    "context": "общий профессиональный контекст",
    "duration": "90",
    "format": "лекция",
    "work_type": "письменная работа",
    "scale": "100",
    "length": "средний",
    "extra": "нет",
}


class SafeDict(dict):
    """Словарь для str.format_map: незаполненные плейсхолдеры остаются как есть,
    а не вызывают KeyError. Защищает от опечаток в шаблонах."""

    def __missing__(self, key):
        return "{" + key + "}"


def load_templates():
    """Загружает библиотеку промптов из templates.json."""
    with open(TEMPLATES_PATH, encoding="utf-8") as f:
        return json.load(f)


def list_templates():
    """Возвращает список шаблонов для меню фронтенда:
    id, name, description и подсказки по необязательным параметрам."""
    templates = load_templates()
    result = []
    for template_id, tpl in templates.items():
        result.append({
            "id": template_id,
            "name": tpl["name"],
            "description": tpl["description"],
            "extra_params": tpl.get("extra_params", {}),
        })
    return result


def build_messages(template_id, params):
    """Собирает список сообщений [{role: system}, {role: user}] из шаблона и
    параметров. Подставляет значения по умолчанию для необязательных полей,
    проверяет обязательные subject и topic. Модель НЕ вызывается — это удобно
    для предпросмотра собранного промпта.

    :param template_id: идентификатор шаблона из templates.json.
    :param params: словарь параметров (subject, topic, level, language, extra и
        необязательные параметры конкретного шаблона).
    :raises ValueError: если шаблон не найден или нет обязательных параметров.
    """
    templates = load_templates()
    if template_id not in templates:
        raise ValueError(f"Неизвестный шаблон: {template_id}")

    tpl = templates[template_id]

    # Проверка обязательных параметров.
    subject = (params.get("subject") or "").strip()
    topic = (params.get("topic") or "").strip()
    if not subject:
        raise ValueError("Не указан обязательный параметр: subject (предмет)")
    if not topic:
        raise ValueError("Не указан обязательный параметр: topic (тема)")

    # Код языка и его человекочитаемое название.
    language = (params.get("language") or "ru").strip().lower()
    if language not in LANGUAGE_NAMES:
        raise ValueError(
            f"Неподдерживаемый язык: {language}. Доступны: {', '.join(LANGUAGE_NAMES)}"
        )
    language_name = LANGUAGE_NAMES[language]

    # Формируем полный набор подстановок: дефолты -> явные значения пользователя.
    values = dict(DEFAULT_PARAMS)
    values.update({
        "subject": subject,
        "topic": topic,
        "level": (params.get("level") or "бакалавриат").strip(),
        "language_name": language_name,
    })
    # Переносим непустые пользовательские значения поверх дефолтов.
    for key, value in params.items():
        if key in ("subject", "topic", "language"):
            continue
        if value is None or str(value).strip() == "":
            continue
        values[key] = str(value)

    system = tpl["system"].format_map(SafeDict(values))
    user = tpl["user"].format_map(SafeDict(values))

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def pick_model(language):
    """Выбирает параметры подключения к модели по языку.

    Маршрутизация:
      - kk            -> KazLLM / Sherkala (KAZ_*),
      - ru / en       -> Qwen3 через OVMS (LLM_*).

    Адреса и имена моделей берутся ТОЛЬКО из переменных окружения.

    :return: словарь {base_url, model, api_key}.
    """
    language = (language or "ru").strip().lower()

    if language == "kk":
        base_url = os.getenv("KAZ_BASE_URL")
        model = os.getenv("KAZ_MODEL")
        api_key = os.getenv("KAZ_API_KEY", "not-needed")
    else:
        base_url = os.getenv("LLM_BASE_URL")
        model = os.getenv("LLM_MODEL")
        api_key = os.getenv("LLM_API_KEY", "not-needed")

    if not base_url or not model:
        raise RuntimeError(
            "Не заданы переменные окружения для модели "
            f"(язык: {language}). Проверьте LLM_BASE_URL/LLM_MODEL "
            "или KAZ_BASE_URL/KAZ_MODEL."
        )

    return {"base_url": base_url, "model": model, "api_key": api_key}


def generate(template_id, params, temperature=0.7, max_tokens=2048):
    """Полный цикл генерации: собирает промпт, выбирает модель по языку и
    вызывает OpenAI-совместимый API.

    :return: словарь с текстом ответа и метаданными (использованная модель, язык).
    :raises ValueError: при ошибках параметров (отдаётся как 400 в app.py).
    :raises RuntimeError: при ошибках модели/сети (отдаётся как 502 в app.py).
    """
    # Импорт здесь, чтобы офлайн-демо и сборка промпта работали без библиотеки openai.
    from openai import OpenAI

    messages = build_messages(template_id, params)
    language = (params.get("language") or "ru").strip().lower()
    model_cfg = pick_model(language)

    client = OpenAI(base_url=model_cfg["base_url"], api_key=model_cfg["api_key"])

    try:
        response = client.chat.completions.create(
            model=model_cfg["model"],
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # noqa: BLE001 — оборачиваем любую ошибку клиента/сети.
        raise RuntimeError(f"Ошибка обращения к модели: {exc}") from exc

    return {
        "content": response.choices[0].message.content,
        "model": model_cfg["model"],
        "language": language,
    }


if __name__ == "__main__":
    # Офлайн-демо: собираем и печатаем промпт БЕЗ вызова модели.
    # Удобно для проверки шаблонов методистами и для отладки.
    print("=== Доступные типы контента ===")
    for item in list_templates():
        print(f"- {item['id']}: {item['name']}")

    print("\n=== Пример собранного промпта (preview, без вызова модели) ===")
    demo_params = {
        "subject": "История Казахстана",
        "topic": "Образование Казахского ханства",
        "level": "бакалавриат",
        "language": "ru",
        "count": "5",
        "extra": "сделать упор на причинно-следственные связи",
    }
    for message in build_messages("test_multiple_choice", demo_params):
        print(f"\n[{message['role'].upper()}]\n{message['content']}")
