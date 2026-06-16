import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Конфигурация Vite.
// base — префикс под-пути на портале. Для сборки агента под
// ai.knus.edu.kz/agents/<slug>/ задаётся аргументом VITE_BASE
// (см. Dockerfile). По умолчанию "/" — для локальной разработки.
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE || "/",
  server: {
    port: 5173,
    // Прокси на backend в режиме разработки: запросы /api/* идут на ядро,
    // поэтому CORS при локальной разработке не нужен.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
