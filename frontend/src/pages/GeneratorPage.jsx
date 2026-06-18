import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getTemplates, preview, generateStream } from "../api.js";
import { useLanguage } from "../i18n/LanguageContext.jsx";

// Русские подписи для необязательных параметров шаблонов (ключи из templates.json).
const PARAM_LABELS = {
  count: "Количество",
  options: "Варианты ответа",
  difficulty: "Сложность",
  depth: "Глубина",
  with_solutions: "С решениями",
  context: "Контекст",
  duration: "Длительность",
  format: "Формат",
  work_type: "Тип работы",
  scale: "Шкала",
  length: "Объём",
};

export default function GeneratorPage() {
  const { templateId } = useParams();
  // Язык генерации берётся из переключателя в навбаре (общий с интерфейсом).
  const { lang, t } = useLanguage();

  const [template, setTemplate] = useState(null);
  const [loadError, setLoadError] = useState("");

  // Состояние формы.
  const [form, setForm] = useState({
    subject: "",
    topic: "",
    level: "бакалавриат",
    extra: "",
    temperature: 0.7,
    max_tokens: 2048,
  });
  // Необязательные параметры конкретного шаблона (extra_params).
  const [extraParams, setExtraParams] = useState({});

  // Результат и состояние запроса.
  const [result, setResult] = useState("");
  const [resultMeta, setResultMeta] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(null); // "preview" | "generate" | null
  const [copied, setCopied] = useState(false);

  // Загружаем описание шаблона (список типов и ищем нужный).
  useEffect(() => {
    let active = true;
    getTemplates()
      .then((list) => {
        if (!active) return;
        const found = list.find((t) => t.id === templateId);
        if (!found) {
          setLoadError("Тип контента не найден: " + templateId);
          return;
        }
        setTemplate(found);
        // Сбрасываем доп.параметры при смене шаблона.
        setExtraParams({});
      })
      .catch((e) => active && setLoadError(e.message));
    return () => {
      active = false;
    };
  }, [templateId]);

  const setField = (name, value) =>
    setForm((f) => ({ ...f, [name]: value }));

  const setExtra = (name, value) =>
    setExtraParams((p) => ({ ...p, [name]: value }));

  // Сборка тела запроса: базовые поля + язык из навбара + непустые доп.параметры.
  const payload = useMemo(() => {
    const body = { template_id: templateId, ...form, language: lang };
    body.temperature = parseFloat(form.temperature);
    body.max_tokens = parseInt(form.max_tokens, 10);
    for (const [k, v] of Object.entries(extraParams)) {
      if (String(v).trim() !== "") body[k] = v;
    }
    return body;
  }, [templateId, form, extraParams, lang]);

  const validate = () => {
    if (!form.subject.trim() || !form.topic.trim()) {
      setError("Заполните обязательные поля: предмет и тема.");
      return false;
    }
    return true;
  };

  const onPreview = async () => {
    setError("");
    if (!validate()) return;
    setBusy("preview");
    try {
      const data = await preview(payload);
      const text = data.messages
        .map((m) => `[${m.role.toUpperCase()}]\n${m.content}`)
        .join("\n\n");
      setResultMeta("Предпросмотр промпта (модель не вызывалась)");
      setResult(text);
    } catch (e) {
      setError(`Ошибка ${e.status ?? ""}: ${e.message}`);
    } finally {
      setBusy(null);
    }
  };

  const onGenerate = async () => {
    setError("");
    if (!validate()) return;
    setBusy("generate");
    setResultMeta("");
    setResult("");
    try {
      let acc = "";
      await generateStream(payload, {
        onMeta: (m) =>
          setResultMeta(
            `Модель: ${m.model} · язык: ${m.language} · ${m.source}`
          ),
        onChunk: (text) => {
          acc += text;
          setResult(acc); // текст наполняется по мере генерации
        },
      });
    } catch (e) {
      setError(`Ошибка ${e.status ?? ""}: ${e.message}`);
    } finally {
      setBusy(null);
    }
  };

  const onCopy = () => {
    navigator.clipboard.writeText(result);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (loadError)
    return (
      <div>
        <div className="error">{loadError}</div>
        <Link to="/" className="back-link">{t("back_to_list")}</Link>
      </div>
    );

  if (!template) return <p className="muted">Загрузка…</p>;

  return (
    <div>
      <Link to="/" className="back-link">{t("back_to_list")}</Link>
      <h1 className="page-title">{template.name}</h1>
      <p className="muted page-subtitle">{template.description}</p>

      <div className="layout">
        {/* ── Форма ── */}
        <section className="card">
          <div className="grid-2">
            <Field label="Предмет *">
              <input
                value={form.subject}
                onChange={(e) => setField("subject", e.target.value)}
                placeholder="напр. История Казахстана"
              />
            </Field>
            <Field label="Тема *">
              <input
                value={form.topic}
                onChange={(e) => setField("topic", e.target.value)}
                placeholder="напр. Казахское ханство"
              />
            </Field>
          </div>

          <Field label="Уровень обучения">
            <input
              value={form.level}
              onChange={(e) => setField("level", e.target.value)}
            />
          </Field>

          {/* Динамические поля шаблона */}
          {Object.entries(template.extra_params || {}).map(([key, hint]) => (
            <Field key={key} label={PARAM_LABELS[key] ?? key} hint={hint}>
              <input
                value={extraParams[key] ?? ""}
                onChange={(e) => setExtra(key, e.target.value)}
              />
            </Field>
          ))}

          <Field label="Дополнительные пожелания">
            <textarea
              rows={3}
              value={form.extra}
              onChange={(e) => setField("extra", e.target.value)}
              placeholder="напр. сделать упор на причинно-следственные связи"
            />
          </Field>

          <div className="grid-2">
            <Field label="Температура" hint="0–2">
              <input
                type="number"
                min="0"
                max="2"
                step="0.1"
                value={form.temperature}
                onChange={(e) => setField("temperature", e.target.value)}
              />
            </Field>
            <Field label="Макс. токенов">
              <input
                type="number"
                min="1"
                max="8192"
                step="1"
                value={form.max_tokens}
                onChange={(e) => setField("max_tokens", e.target.value)}
              />
            </Field>
          </div>

          <div className="buttons">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={onPreview}
              disabled={busy !== null}
            >
              {busy === "preview" ? "Сборка…" : "Предпросмотр промпта"}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={onGenerate}
              disabled={busy !== null}
            >
              {busy === "generate" ? "Генерация…" : "Сгенерировать"}
            </button>
          </div>
        </section>

        {/* ── Результат ── */}
        <section className="card">
          <h2 className="card-title">Результат</h2>
          {error && <div className="error">{error}</div>}
          {resultMeta && <div className="result-meta">{resultMeta}</div>}
          <div className="result">
            {result || "Заполните параметры и нажмите «Сгенерировать»."}
          </div>
          {result && (
            <button type="button" className="btn btn-copy" onClick={onCopy}>
              {copied ? "Скопировано ✓" : "Скопировать"}
            </button>
          )}
        </section>
      </div>
    </div>
  );
}

// Небольшой компонент поля с подписью и подсказкой.
function Field({ label, hint, children }) {
  return (
    <label className="field">
      <span className="field__label">
        {label} {hint && <span className="field__hint">{hint}</span>}
      </span>
      {children}
    </label>
  );
}
