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


# Резервная (облачная) модель — Gemini. Используется, когда локальная модель
# недоступна, и для ресёрч-запросов (prefer_fallback=True). Имя модели всегда
# передаётся явно — иначе шлюз берёт дорогую по умолчанию.
DEFAULT_FALLBACK_MODEL = "gemini-3.1-flash-lite"


def pick_model(language):
    """Параметры ОСНОВНОЙ (локальной) модели по языку.

    Маршрутизация:
      - kk      -> KAZ_* (если заданы), иначе общий эндпоинт LLM_*,
      - ru / en -> LLM_*.

    Если эндпоинт/модель не заданы — поля будут None (тогда генерация уйдёт
    на резервную модель, см. generate()).

    :return: словарь {base_url, model, api_key}.
    """
    language = (language or "ru").strip().lower()

    if language == "kk":
        base_url = os.getenv("KAZ_BASE_URL") or os.getenv("LLM_BASE_URL")
        model = os.getenv("KAZ_MODEL") or os.getenv("LLM_MODEL")
        api_key = os.getenv("KAZ_API_KEY") or os.getenv("LLM_API_KEY", "not-needed")
    else:
        base_url = os.getenv("LLM_BASE_URL")
        model = os.getenv("LLM_MODEL")
        api_key = os.getenv("LLM_API_KEY", "not-needed")

    return {"base_url": base_url, "model": model, "api_key": api_key}


def pick_fallback_model():
    """Параметры РЕЗЕРВНОЙ (облачной) модели Gemini.

    Имя модели — из FALLBACK_MODEL, по умолчанию gemini-3.1-flash-lite.
    Если FALLBACK_BASE_URL не задан — резерва нет.

    :return: словарь {base_url, model, api_key}.
    """
    return {
        "base_url": os.getenv("FALLBACK_BASE_URL"),
        "model": os.getenv("FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL),
        "api_key": os.getenv("FALLBACK_API_KEY", "not-needed"),
    }


def _call_model(cfg, messages, temperature, max_tokens):
    """Один вызов OpenAI-совместимого API. Имя модели передаётся ЯВНО."""
    from openai import OpenAI

    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
    response = client.chat.completions.create(
        model=cfg["model"],
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def generate(template_id, params, temperature=0.7, max_tokens=2048,
             prefer_fallback=False):
    """Полный цикл генерации с резервированием.

    Порядок: ОСНОВНАЯ (локальная) модель -> при сбое РЕЗЕРВНАЯ (Gemini).
    Если prefer_fallback=True (например, ресёрч-запрос) — сразу Gemini, а
    локальная остаётся как запасной вариант.

    :return: словарь с текстом, использованной моделью, языком и источником
        ("основная"/"резервная").
    :raises ValueError: при ошибках параметров (отдаётся как 400 в app.py).
    :raises RuntimeError: если все эндпоинты недоступны (отдаётся как 502).
    """
    messages = build_messages(template_id, params)
    language = (params.get("language") or "ru").strip().lower()

    primary = pick_model(language)
    fallback = pick_fallback_model()

    # Кандидат пригоден, только если заданы и адрес, и имя модели
    # (иначе шлюз получил бы пустую модель и взял дорогую по умолчанию).
    primary_ok = bool(primary["base_url"] and primary["model"])
    fallback_ok = bool(fallback["base_url"] and fallback["model"])

    primary_attempt = ("основная", primary)
    fallback_attempt = ("резервная", fallback)

    # Порядок попыток.
    attempts = []
    if prefer_fallback:
        if fallback_ok:
            attempts.append(fallback_attempt)
        if primary_ok:
            attempts.append(primary_attempt)
    else:
        if primary_ok:
            attempts.append(primary_attempt)
        if fallback_ok:
            attempts.append(fallback_attempt)

    if not attempts:
        raise RuntimeError(
            "Не настроен ни основной (LLM_BASE_URL + LLM_MODEL), ни резервный "
            "(FALLBACK_BASE_URL) эндпоинт. Проверьте .env."
        )

    last_error = None
    for source, cfg in attempts:
        try:
            content = _call_model(cfg, messages, temperature, max_tokens)
            return {
                "content": content,
                "model": cfg["model"],
                "language": language,
                "source": source,
            }
        except Exception as exc:  # noqa: BLE001 — пробуем следующий эндпоинт.
            last_error = exc
            continue

    raise RuntimeError(
        f"Все эндпоинты недоступны. Последняя ошибка: {last_error}"
    )


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
