import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getTemplates } from "../api.js";
import { useLanguage } from "../i18n/LanguageContext.jsx";

// Главная: карточки типов контента. Клик ведёт на страницу генератора.
export default function HomePage() {
  const { t } = useLanguage();
  const [templates, setTemplates] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTemplates()
      .then(setTemplates)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted">{t("loading_types")}</p>;

  if (error)
    return (
      <div className="error">
        {t("load_error")} {error}
        <br />
        {t("check_backend")}
      </div>
    );

  return (
    <div>
      <h1 className="page-title">{t("home_title")}</h1>
      <p className="page-subtitle">{t("home_subtitle")}</p>
      <div className="cards">
        {templates.map((tpl) => (
          <Link key={tpl.id} to={`/generate/${tpl.id}`} className="card-link">
            <h3>{tpl.name}</h3>
            <p>{tpl.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
