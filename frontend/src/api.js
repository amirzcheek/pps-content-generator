// Клиент backend-ядра генератора.
// Адрес берётся из переменной окружения VITE_API_BASE (см. .env.example).
// По умолчанию — относительный путь /api (прокси Vite в dev, reverse-proxy на проде).
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

// Общий помощник: разбирает ответ и поднимает осмысленную ошибку (400/502 и пр.).
async function request(path, options) {
  let res;
  try {
    res = await fetch(API_BASE + path, options);
  } catch (e) {
    throw new Error("Сеть недоступна или backend не запущен. " + e.message);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail
      ? typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail)
      : "HTTP " + res.status;
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return data;
}

// Список типов контента для меню.
export function getTemplates() {
  return request("/templates").then((d) => d.templates);
}

// Сборка промпта без вызова модели (предпросмотр).
export function preview(payload) {
  return request("/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// Полная генерация через модель (без потока) — для n8n и простых клиентов.
export function generate(payload) {
  return request("/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// Потоковая генерация (SSE): текст приходит по мере готовности.
// Колбэки: onMeta({source, model, language}), onChunk(text).
// Бросает Error при ошибке (в т.ч. событие error из потока).
export async function generateStream(payload, { onMeta, onChunk } = {}) {
  let res;
  try {
    res = await fetch(API_BASE + "/generate/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    throw new Error("Сеть недоступна или backend не запущен. " + e.message);
  }
  if (!res.ok || !res.body) {
    const data = await res.json().catch(() => ({}));
    const err = new Error(data.detail || "HTTP " + res.status);
    err.status = res.status;
    throw err;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // Разбираем поток событий SSE: блоки разделены "\n\n", полезная нагрузка в "data:".
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep;
    while ((sep = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const line = block.replace(/^data:\s?/, "").trim();
      if (!line) continue;

      let ev;
      try {
        ev = JSON.parse(line);
      } catch {
        continue;
      }
      if (ev.type === "meta") onMeta?.(ev);
      else if (ev.type === "chunk") onChunk?.(ev.text);
      else if (ev.type === "error") throw new Error(ev.detail || "Ошибка генерации");
      // "done" — поток завершён успешно.
    }
  }
}
