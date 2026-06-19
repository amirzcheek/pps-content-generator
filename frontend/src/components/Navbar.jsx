import { Link } from "react-router-dom";

import { useI18n, LangSwitcher } from "../i18n.jsx";
import { useSession } from "../auth/useSession.js";

// Базовый адрес портала (бренд, выход, админка ведут туда).
// Переопределяется через VITE_PORTAL_URL, по умолчанию — прод-портал.
const PORTAL = import.meta.env.VITE_PORTAL_URL ?? "https://ai.knus.edu.kz";

// Навбар портала ai.knus.edu.kz, адаптированный под этого агента.
// Ссылка «Админка» видна только администраторам (user.isAdmin из сессии).
export default function Navbar() {
  const { t } = useI18n();
  const { user } = useSession();

  return (
    <header className="topbar">
      <div className="topbar-left">
        <a className="brand" href={`${PORTAL}/`}>
          KNUS Digital
        </a>
        <span className="brand-sep">/</span>
        <Link className="brand-agent" to="/">
          {t("agent_name")}
        </Link>

        <LangSwitcher />
      </div>

      <div className="topbar-right">
        {user.displayName && (
          <span className="user-name">{user.displayName}</span>
        )}
        {/* Видна только администраторам */}
        {user.isAdmin && (
          <a className="admin-link" href={`${PORTAL}/admin`}>
            {t("admin")}
          </a>
        )}
        <a className="logout-btn" href={`${PORTAL}/`}>
          {t("to_portal")}
        </a>
      </div>
    </header>
  );
}
