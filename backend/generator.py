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

# Qwen3 — рассуждающая модель: без этого флага она пишет <think>…</think> перед
# ответом, тратя токены и время. Отключаем размышления через chat_template_kwargs
# (OVMS/Qwen3). Применяется ТОЛЬКО к локальной модели; Gemini такого не понимает.
NO_THINKING_EXTRA_BODY = {"chat_template_kwargs": {"enable_thinking": False}}


def _llm_timeout():
    """Таймаут запроса к модели в секундах (CPU-инференс медленный)."""
    try:
        return int(os.getenv("LLM_TIMEOUT", "300"))
    except ValueError:
        return 300


def _disable_thinking():
    """Отключать ли размышления Qwen (по умолчанию да). Переопределяется
    переменной LLM_DISABLE_THINKING (false — оставить как есть)."""
    return os.getenv("LLM_DISABLE_THINKING", "true").strip().lower() not in (
        "0", "false", "no", "off",
    )


def pick_model(language):
    """Параметры ОСНОВНОЙ (локальной) модели по языку.

    Маршрутизация:
      - kk      -> KAZ_* (если заданы), иначе общий эндпоинт LLM_*,
      - ru / en -> LLM_*.

    Если эндпоинт/модель не заданы — поля будут None (тогда генерация уйдёт
    на резервную модель, см. generate()).

    :return: словарь {base_url, model, api_key, extra_body}.
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

    return {
        "base_url": base_url,
        "model": model,
        "api_key": api_key,
        # Для локальной (Qwen3) отключаем <think>; для прочих можно выключить env-ом.
        "extra_body": NO_THINKING_EXTRA_BODY if _disable_thinking() else None,
    }


def pick_fallback_model():
    """Параметры РЕЗЕРВНОЙ (облачной) модели Gemini.

    Имя модели — из FALLBACK_MODEL, по умолчанию gemini-3.1-flash-lite.
    Если FALLBACK_BASE_URL не задан — резерва нет.

    :return: словарь {base_url, model, api_key, extra_body}.
    """
    return {
        "base_url": os.getenv("FALLBACK_BASE_URL"),
        "model": os.getenv("FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL),
        "api_key": os.getenv("FALLBACK_API_KEY", "not-needed"),
        # Gemini не понимает chat_template_kwargs — extra_body не передаём.
        "extra_body": None,
    }


def _ordered_attempts(language, prefer_fallback):
    """Список попыток [(источник, cfg), ...] в нужном порядке.

    Кандидат пригоден, только если заданы и адрес, и имя модели (иначе шлюз
    получил бы пустую модель). При prefer_fallback резервная идёт первой.
    """
    primary = pick_model(language)
    fallback = pick_fallback_model()
    primary_ok = bool(primary["base_url"] and primary["model"])
    fallback_ok = bool(fallback["base_url"] and fallback["model"])

    order = []
    if prefer_fallback:
        if fallback_ok:
            order.append(("резервная", fallback))
        if primary_ok:
            order.append(("основная", primary))
    else:
        if primary_ok:
            order.append(("основная", primary))
        if fallback_ok:
            order.append(("резервная", fallback))
    return order


def _create_completion(cfg, messages, temperature, max_tokens, stream):
    """Вызов OpenAI-совместимого API. Имя модели передаётся ЯВНО, для локальной
    модели добавляется extra_body (отключение размышлений), задаётся timeout."""
    from openai import OpenAI

    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
    kwargs = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
        "timeout": _llm_timeout(),
    }
    if cfg.get("extra_body"):
        kwargs["extra_body"] = cfg["extra_body"]
    return client.chat.completions.create(**kwargs)


def _iter_text(stream):
    """Извлекает текстовые куски из потокового ответа OpenAI SDK."""
    for chunk in stream:
        if not getattr(chunk, "choices", None):
            continue
        delta = chunk.choices[0].delta
        text = getattr(delta, "content", None)
        if text:
            yield text


def generate(template_id, params, temperature=0.7, max_tokens=2048,
             prefer_fallback=False):
    """Полный цикл генерации с резервированием (без потока).

    Порядок: ОСНОВНАЯ (локальная) -> при сбое РЕЗЕРВНАЯ (Gemini). При
    prefer_fallback=True (ресёрч) — сразу Gemini, локальная как запасная.

    :return: словарь {content, model, language, source}.
    :raises ValueError: при ошибках параметров (400 в app.py).
    :raises RuntimeError: если все эндпоинты недоступны (502 в app.py).
    """
    messages = build_messages(template_id, params)
    language = (params.get("language") or "ru").strip().lower()
    attempts = _ordered_attempts(language, prefer_fallback)

    if not attempts:
        raise RuntimeError(
            "Не настроен ни основной (LLM_BASE_URL + LLM_MODEL), ни резервный "
            "(FALLBACK_BASE_URL) эндпоинт. Проверьте .env."
        )

    last_error = None
    for source, cfg in attempts:
        try:
            response = _create_completion(
                cfg, messages, temperature, max_tokens, stream=False
            )
            return {
                "content": response.choices[0].message.content,
                "model": cfg["model"],
                "language": language,
                "source": source,
            }
        except Exception as exc:  # noqa: BLE001 — пробуем следующий эндпоинт.
            last_error = exc
            continue

    raise RuntimeError(f"Все эндпоинты недоступны. Последняя ошибка: {last_error}")


def stream_generate(template_id, params, temperature=0.7, max_tokens=2048,
                    prefer_fallback=False):
    """Потоковая генерация: отдаёт словари-события по мере поступления текста.

    События:
      {"type":"meta",  "source","model","language"}  — один раз перед текстом;
      {"type":"chunk", "text": "..."}                — куски текста;
      {"type":"done"}                                — успешное завершение;
      {"type":"error", "detail": "..."}              — ошибка.

    Резерв срабатывает, только если основная модель не отдала ни одного куска
    (сбой соединения до начала ответа). После старта потока ошибки не приводят
    к переключению — отдаётся событие error.
    """
    try:
        messages = build_messages(template_id, params)
    except ValueError as exc:
        yield {"type": "error", "detail": str(exc)}
        return

    language = (params.get("language") or "ru").strip().lower()
    attempts = _ordered_attempts(language, prefer_fallback)
    if not attempts:
        yield {"type": "error", "detail": "Не настроен ни основной, ни резервный "
                                          "эндпоинт. Проверьте .env."}
        return

    last_error = None
    for source, cfg in attempts:
        try:
            stream = _create_completion(
                cfg, messages, temperature, max_tokens, stream=True
            )
            iterator = _iter_text(stream)
            # Первый кусок — здесь всплывают ошибки соединения; до него можно
            # переключиться на резерв.
            first = next(iterator, "")
        except Exception as exc:  # noqa: BLE001 — пробуем следующий эндпоинт.
            last_error = exc
            continue

        # Зафиксировали источник — дальше переключений нет.
        yield {"type": "meta", "source": source, "model": cfg["model"],
               "language": language}
        try:
            if first:
                yield {"type": "chunk", "text": first}
            for text in iterator:
                yield {"type": "chunk", "text": text}
            yield {"type": "done"}
        except Exception as exc:  # noqa: BLE001 — поток оборвался после старта.
            yield {"type": "error", "detail": f"Поток прерван: {exc}"}
        return

    yield {"type": "error",
           "detail": f"Все эндпоинты недоступны. Последняя ошибка: {last_error}"}


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
