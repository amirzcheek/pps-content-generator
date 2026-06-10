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

// Полная генерация через модель.
export function generate(payload) {
  return request("/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
