import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import App from "./App.jsx";
import HomePage from "./pages/HomePage.jsx";
import GeneratorPage from "./pages/GeneratorPage.jsx";
import { LangProvider } from "./i18n.jsx";
import "./index.css";

// Маршруты приложения. App — общий layout (шапка + <Outlet/>).
// basename = префикс под-пути портала (Vite base), чтобы ссылки react-router
// строились относительно /agents/<slug>/. В dev base = "/".
const basename = (import.meta.env.BASE_URL || "/").replace(/\/$/, "") || "/";

const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <App />,
      children: [
        { index: true, element: <HomePage /> },
        { path: "generate/:templateId", element: <GeneratorPage /> },
      ],
    },
  ],
  { basename }
);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <LangProvider>
      <RouterProvider router={router} />
    </LangProvider>
  </React.StrictMode>
);
