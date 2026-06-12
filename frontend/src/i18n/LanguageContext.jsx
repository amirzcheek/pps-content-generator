import { createContext, useCallback, useContext, useState } from "react";

// Строки интерфейса для трёх языков портала (ru / kk / en).
// Язык интерфейса совпадает с языком генерации (передаётся в backend).
const STRINGS = {
  ru: {
    agent_name: "Генератор контента",
    admin: "Админка",
    to_portal: "Вернуться на портал",
    home_title: "Генератор учебного контента",
    home_subtitle:
      "Выберите тип материала. Тексты создаются на локальных моделях вуза.",
    loading_types: "Загрузка типов контента…",
    load_error: "Не удалось загрузить список типов:",
    check_backend: "Проверьте, что backend запущен и доступен.",
    back_to_list: "← К списку типов",
  },
  kk: {
    agent_name: "Контент генераторы",
    admin: "Әкімші панелі",
    to_portal: "Порталға оралу",
    home_title: "Оқу контентін генераторы",
    home_subtitle:
      "Материал түрін таңдаңыз. Мәтіндер университеттің жергілікті модельдерінде жасалады.",
    loading_types: "Контент түрлері жүктелуде…",
    load_error: "Түрлер тізімін жүктеу мүмкін болмады:",
    check_backend: "Backend іске қосылғанын және қолжетімді екенін тексеріңіз.",
    back_to_list: "← Түрлер тізіміне",
  },
  en: {
    agent_name: "Content Generator",
    admin: "Admin panel",
    to_portal: "Back to portal",
    home_title: "Learning Content Generator",
    home_subtitle:
      "Choose a material type. Texts are produced by the university's local models.",
    loading_types: "Loading content types…",
    load_error: "Failed to load the list of types:",
    check_backend: "Make sure the backend is running and reachable.",
    back_to_list: "← Back to types",
  },
};

const LANG_KEY = "coursehub_lang"; // тот же ключ, что и на портале — язык синхронизируется
const LangContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    const saved = localStorage.getItem(LANG_KEY);
    return STRINGS[saved] ? saved : "ru";
  });

  const setLang = useCallback((next) => {
    if (!STRINGS[next]) return;
    localStorage.setItem(LANG_KEY, next);
    document.documentElement.lang = next;
    setLangState(next);
  }, []);

  // Переводчик строк интерфейса.
  const t = useCallback(
    (key) => STRINGS[lang][key] ?? STRINGS.ru[key] ?? key,
    [lang]
  );

  return (
    <LangContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useLanguage используется вне LanguageProvider");
  return ctx;
}
