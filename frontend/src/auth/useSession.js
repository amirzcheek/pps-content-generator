import { useEffect, useState } from "react";

// Хук сессии пользователя — заглушка под вход платформы / Azure AD SSO.
//
// На портале ai.knus.edu.kz сессию отдаёт эндпоинт /api/auth/session в виде
//   { user: { displayName, isAdmin, ... } }
// и именно поле isAdmin управляет показом ссылки «Админка» в навбаре.
//
// Когда агент встроен в портал, запрос проходит через серверный прокси и
// возвращает реальную сессию. Локально (SSO ещё не подключён) эндпоинта нет —
// тогда graceful fallback на «гостя». Чтобы посмотреть админ-вид при разработке,
// задайте VITE_PREVIEW_ADMIN=true в frontend/.env.
const FALLBACK_USER = {
  displayName: "",
  isAdmin: import.meta.env.VITE_PREVIEW_ADMIN === "true",
};

export function useSession() {
  const [user, setUser] = useState(FALLBACK_USER);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    fetch("/api/auth/session", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (active && data && data.user) setUser(data.user);
      })
      .catch(() => {
        /* нет сессии — остаёмся на fallback (гость, не админ) */
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { user, loading };
}
