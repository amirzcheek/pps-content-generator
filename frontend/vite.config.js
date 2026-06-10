import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Конфигурация Vite.
// base: "/" — если интерфейс будет размещён в подкаталоге портала
// (например ai.knus.edu.kz/content-generator/), поменяйте на "/content-generator/".
export default defineConfig({
  plugins: [react()],
  base: "/",
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
