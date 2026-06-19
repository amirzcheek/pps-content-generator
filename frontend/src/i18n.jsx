import { createContext, useContext, useState, useCallback, useMemo } from "react";

export const LANG_KEY = "coursehub_lang";
const LANGS = ["ru", "kk", "en"];

export const i18n = {
  ru: {
    // Навбар
    agent_name: "Генератор контента",
    admin: "Админка",
    to_portal: "Вернуться на портал",
    // Главная
    home_title: "Генератор учебного контента",
    home_subtitle:
      "Выберите тип материала. Тексты создаются на локальных моделях вуза.",
    home_loading: "Загрузка типов контента…",
    home_load_error: "Не удалось загрузить список типов:",
    home_check_backend: "Проверьте, что backend запущен и доступен.",
    // Страница генератора
    back_to_list: "← К списку типов",
    loading: "Загрузка…",
    err_template_not_found: "Тип контента не найден: {id}",
    f_subject: "Предмет",
    f_topic: "Тема",
    f_level: "Уровень обучения",
    level_default: "бакалавриат",
    f_extra: "Дополнительные пожелания",
    f_temperature: "Температура",
    f_max_tokens: "Макс. токенов",
    ph_subject: "напр. История Казахстана",
    ph_topic: "напр. Казахское ханство",
    ph_extra: "напр. сделать упор на причинно-следственные связи",
    // Подписи необязательных параметров шаблонов
    param_count: "Количество",
    param_options: "Варианты ответа",
    param_difficulty: "Сложность",
    param_depth: "Глубина",
    param_with_solutions: "С решениями",
    param_context: "Контекст",
    param_duration: "Длительность",
    param_format: "Формат",
    param_work_type: "Тип работы",
    param_scale: "Шкала",
    param_length: "Объём",
    // Кнопки и результат
    btn_preview: "Предпросмотр промпта",
    btn_preview_busy: "Сборка…",
    btn_generate: "Сгенерировать",
    btn_stop: "Остановить",
    result_title: "Результат",
    result_placeholder: "Заполните параметры и нажмите «Сгенерировать».",
    btn_copy: "Скопировать",
    btn_copied: "Скопировано ✓",
    preview_meta: "Предпросмотр промпта (модель не вызывалась)",
    meta_line: "Модель: {model} · язык: {lang} · {source}",
    stopped_suffix: "остановлено",
    stopped: "Остановлено",
    err_required: "Заполните обязательные поля: предмет и тема.",
    err_generic: "Ошибка {status}: {message}",
    source_primary: "основная",
    source_fallback: "резервная",
    lang_ru: "русский",
    lang_kk: "казахский",
    lang_en: "английский",
  },

  kk: {
    agent_name: "Контент генераторы",
    admin: "Әкімші панелі",
    to_portal: "Порталға оралу",
    home_title: "Оқу контентінің генераторы",
    home_subtitle:
      "Материал түрін таңдаңыз. Мәтіндер университеттің жергілікті модельдерінде жасалады.",
    home_loading: "Контент түрлері жүктелуде…",
    home_load_error: "Түрлер тізімін жүктеу мүмкін болмады:",
    home_check_backend: "Backend іске қосылғанын және қолжетімді екенін тексеріңіз.",
    back_to_list: "← Түрлер тізіміне",
    loading: "Жүктелуде…",
    err_template_not_found: "Контент түрі табылмады: {id}",
    f_subject: "Пән",
    f_topic: "Тақырып",
    f_level: "Оқыту деңгейі",
    level_default: "бакалавриат",
    f_extra: "Қосымша тілектер",
    f_temperature: "Температура",
    f_max_tokens: "Макс. токендер",
    ph_subject: "мыс. Қазақстан тарихы",
    ph_topic: "мыс. Қазақ хандығы",
    ph_extra: "мыс. себеп-салдар байланыстарына назар аудару",
    param_count: "Саны",
    param_options: "Жауап нұсқалары",
    param_difficulty: "Күрделілігі",
    param_depth: "Тереңдігі",
    param_with_solutions: "Шешімдерімен",
    param_context: "Контекст",
    param_duration: "Ұзақтығы",
    param_format: "Формат",
    param_work_type: "Жұмыс түрі",
    param_scale: "Шкала",
    param_length: "Көлемі",
    btn_preview: "Промптты алдын ала қарау",
    btn_preview_busy: "Жинақталуда…",
    btn_generate: "Генерациялау",
    btn_stop: "Тоқтату",
    result_title: "Нәтиже",
    result_placeholder: "Параметрлерді толтырып, «Генерациялау» батырмасын басыңыз.",
    btn_copy: "Көшіру",
    btn_copied: "Көшірілді ✓",
    preview_meta: "Промптты алдын ала қарау (модель шақырылмады)",
    meta_line: "Модель: {model} · тіл: {lang} · {source}",
    stopped_suffix: "тоқтатылды",
    stopped: "Тоқтатылды",
    err_required: "Міндетті өрістерді толтырыңыз: пән және тақырып.",
    err_generic: "Қате {status}: {message}",
    source_primary: "негізгі",
    source_fallback: "резервтік",
    lang_ru: "орысша",
    lang_kk: "қазақша",
    lang_en: "ағылшынша",
  },

  en: {
    agent_name: "Content Generator",
    admin: "Admin panel",
    to_portal: "Back to portal",
    home_title: "Learning Content Generator",
    home_subtitle:
      "Choose a material type. Texts are produced by the university's local models.",
    home_loading: "Loading content types…",
    home_load_error: "Failed to load the list of types:",
    home_check_backend: "Make sure the backend is running and reachable.",
    back_to_list: "← Back to types",
    loading: "Loading…",
    err_template_not_found: "Content type not found: {id}",
    f_subject: "Subject",
    f_topic: "Topic",
    f_level: "Education level",
    level_default: "Bachelor's",
    f_extra: "Additional notes",
    f_temperature: "Temperature",
    f_max_tokens: "Max tokens",
    ph_subject: "e.g. History of Kazakhstan",
    ph_topic: "e.g. Kazakh Khanate",
    ph_extra: "e.g. emphasize cause-and-effect relations",
    param_count: "Count",
    param_options: "Answer options",
    param_difficulty: "Difficulty",
    param_depth: "Depth",
    param_with_solutions: "With solutions",
    param_context: "Context",
    param_duration: "Duration",
    param_format: "Format",
    param_work_type: "Work type",
    param_scale: "Scale",
    param_length: "Length",
    btn_preview: "Preview prompt",
    btn_preview_busy: "Building…",
    btn_generate: "Generate",
    btn_stop: "Stop",
    result_title: "Result",
    result_placeholder: 'Fill in the fields and click "Generate".',
    btn_copy: "Copy",
    btn_copied: "Copied ✓",
    preview_meta: "Prompt preview (model was not called)",
    meta_line: "Model: {model} · language: {lang} · {source}",
    stopped_suffix: "stopped",
    stopped: "Stopped",
    err_required: "Fill in the required fields: subject and topic.",
    err_generic: "Error {status}: {message}",
    source_primary: "primary",
    source_fallback: "fallback",
    lang_ru: "Russian",
    lang_kk: "Kazakh",
    lang_en: "English",
  },
};

function detectLang() {
  const saved = localStorage.getItem(LANG_KEY);
  if (saved && i18n[saved]) return saved;
  const b = (navigator.language || "ru").toLowerCase();
  if (b.startsWith("kk")) return "kk";
  if (b.startsWith("en")) return "en";
  return "ru";
}

const LangCtx = createContext(null);

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(detectLang);
  const setLang = useCallback((l) => {
    if (!i18n[l]) return;
    localStorage.setItem(LANG_KEY, l);
    document.documentElement.lang = l;
    setLangState(l);
  }, []);
  const t = useCallback(
    (key, vars = {}) => {
      const tpl = i18n[lang]?.[key] ?? i18n.ru[key] ?? "";
      return tpl.replace(/\{(\w+)\}/g, (_, n) => String(vars[n] ?? ""));
    },
    [lang]
  );
  const locale = lang === "kk" ? "kk-KZ" : lang === "en" ? "en-US" : "ru-RU";
  const value = useMemo(
    () => ({ lang, setLang, t, locale }),
    [lang, setLang, t, locale]
  );
  return <LangCtx.Provider value={value}>{children}</LangCtx.Provider>;
}

export function useI18n() {
  const ctx = useContext(LangCtx);
  if (!ctx) throw new Error("useI18n must be used within <LangProvider>");
  return ctx;
}

export function LangSwitcher() {
  const { lang, setLang } = useI18n();
  return (
    <div className="lang-switch">
      {[
        ["ru", "RU"],
        ["kk", "KZ"],
        ["en", "EN"],
      ].map(([code, label]) => (
        <button
          key={code}
          type="button"
          className={"lang-btn" + (lang === code ? " active" : "")}
          onClick={() => setLang(code)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
