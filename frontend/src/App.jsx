import { Link, Outlet } from "react-router-dom";

// Общий каркас приложения: шапка с ссылкой на главную + область маршрута.
export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__inner">
          <Link to="/" className="app-header__title">
            Генератор учебного контента для ППС
          </Link>
          <span className="app-header__sub">ai.knus.edu.kz</span>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
