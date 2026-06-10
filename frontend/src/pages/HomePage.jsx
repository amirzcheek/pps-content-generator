import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getTemplates } from "../api.js";

// Главная: карточки типов контента. Клик ведёт на страницу генератора.
export default function HomePage() {
  const [templates, setTemplates] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTemplates()
      .then(setTemplates)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted">Загрузка типов контента…</p>;

  if (error)
    return (
      <div className="error">
        Не удалось загрузить список типов: {error}
        <br />
        Проверьте, что backend запущен и доступен.
      </div>
    );

  return (
    <div>
      <h1 className="page-title">Выберите тип материала</h1>
      <p className="muted page-subtitle">
        Сервис генерирует учебные материалы на базе локальных моделей вуза.
      </p>
      <div className="cards">
        {templates.map((t) => (
          <Link key={t.id} to={`/generate/${t.id}`} className="card-link">
            <h3>{t.name}</h3>
            <p>{t.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
