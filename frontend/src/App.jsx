import { Outlet } from "react-router-dom";

import Navbar from "./components/Navbar.jsx";

// Общий каркас приложения в стиле портала: page > wrap > navbar + маршрут.
export default function App() {
  return (
    <div className="page">
      <div className="wrap">
        <Navbar />
        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
