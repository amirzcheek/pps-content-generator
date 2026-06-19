import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getTemplates, preview, generateStream } from "../api.js";
import { useI18n } from "../i18n.jsx";

export default function GeneratorPage() {
  const { templateId } = useParams();
  // Язык генерации и интерфейса — общий, из переключателя в навбаре.
  const { lang, t } = useI18n();

  const [template, setTemplate] = useState(null);
  const [loadError, setLoadError] = useState("");

  // Состояние формы (уровень по умолчанию — из перевода).
  const [form, setForm] = useState(() => ({
    subject: "",
    topic: "",
    level: t("level_default"),
    extra: "",
    temperature: 0.7,
    max_tokens: 2048,
  }));
  // Необязательные параметры конкретного шаблона (extra_params).
  const [extraParams, setExtraParams] = useState({});

  // Результат и состояние запроса.
  const [result, setResult] = useState("");
  const [resultMeta, setResultMeta] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(null); // "preview" | "generate" | null
  const [copied, setCopied] = useState(false);
  // Контроллер для остановки потоковой генерации пользователем.
  const abortRef = useRef(null);

  // Загружаем описание шаблона (на текущем языке) и ищем нужный.
  // Перезагрузка при смене языка обновляет название/описание/подсказки.
  useEffect(() => {
    let active = true;
    getTemplates(lang)
      .then((list) => {
        if (!active) return;
        const found = list.find((item) => item.id === templateId);
        if (!found) {
          setLoadError(t("err_template_not_found", { id: templateId }));
          return;
        }
        setLoadError("");
        setTemplate(found);
      })
      .catch((e) => active && setLoadError(e.message));
    return () => {
      active = false;
    };
  }, [templateId, lang]);

  // Сбрасываем доп.параметры только при смене типа контента (не при смене языка).
  useEffect(() => {
    setExtraParams({});
  }, [templateId]);

  const setField = (name, value) =>
    setForm((f) => ({ ...f, [name]: value }));

  const setExtra = (name, value) =>
    setExtraParams((p) => ({ ...p, [name]: value }));

  // Сборка тела запроса: базовые поля + язык из навбара (поле lang) + доп.параметры.
  const payload = useMemo(() => {
    const body = { template_id: templateId, ...form, lang };
    body.temperature = parseFloat(form.temperature);
    body.max_tokens = parseInt(form.max_tokens, 10);
    for (const [k, v] of Object.entries(extraParams)) {
      if (String(v).trim() !== "") body[k] = v;
    }
    return body;
  }, [templateId, form, extraParams, lang]);

  const validate = () => {
    if (!form.subject.trim() || !form.topic.trim()) {
      setError(t("err_required"));
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
      setResultMeta(t("preview_meta"));
      setResult(text);
    } catch (e) {
      setError(t("err_generic", { status: e.status ?? "", message: e.message }));
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

    const controller = new AbortController();
    abortRef.current = controller;
    let metaStr = "";
    try {
      let acc = "";
      await generateStream(payload, {
        signal: controller.signal,
        onMeta: (m) => {
          const langName = t(`lang_${m.language}`) || m.language;
          const src = t(
            m.source === "основная" ? "source_primary" : "source_fallback"
          );
          metaStr = t("meta_line", { model: m.model, lang: langName, source: src });
          setResultMeta(metaStr);
        },
        onChunk: (text) => {
          acc += text;
          setResult(acc); // текст наполняется по мере генерации
        },
      });
      // Пользователь нажал «Остановить» — помечаем, текст оставляем как есть.
      if (controller.signal.aborted) {
        setResultMeta(
          metaStr ? `${metaStr} · ${t("stopped_suffix")}` : t("stopped")
        );
      }
    } catch (e) {
      setError(t("err_generic", { status: e.status ?? "", message: e.message }));
    } finally {
      abortRef.current = null;
      setBusy(null);
    }
  };

  // Остановить идущую генерацию.
  const onStop = () => abortRef.current?.abort();

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

  if (!template) return <p className="muted">{t("loading")}</p>;

  return (
    <div>
      <Link to="/" className="back-link">{t("back_to_list")}</Link>
      <h1 className="page-title">{template.name}</h1>
      <p className="muted page-subtitle">{template.description}</p>

      <div className="layout">
        {/* ── Форма ── */}
        <section className="card">
          <div className="grid-2">
            <Field label={`${t("f_subject")} *`}>
              <input
                value={form.subject}
                onChange={(e) => setField("subject", e.target.value)}
                placeholder={t("ph_subject")}
              />
            </Field>
            <Field label={`${t("f_topic")} *`}>
              <input
                value={form.topic}
                onChange={(e) => setField("topic", e.target.value)}
                placeholder={t("ph_topic")}
              />
            </Field>
          </div>

          <Field label={t("f_level")}>
            <input
              value={form.level}
              onChange={(e) => setField("level", e.target.value)}
            />
          </Field>

          {/* Динамические поля шаблона (подпись — переводимая, подсказка — из шаблона) */}
          {Object.entries(template.extra_params || {}).map(([key, hint]) => (
            <Field key={key} label={t("param_" + key) || key} hint={hint}>
              <input
                value={extraParams[key] ?? ""}
                onChange={(e) => setExtra(key, e.target.value)}
              />
            </Field>
          ))}

          <Field label={t("f_extra")}>
            <textarea
              rows={3}
              value={form.extra}
              onChange={(e) => setField("extra", e.target.value)}
              placeholder={t("ph_extra")}
            />
          </Field>

          <div className="grid-2">
            <Field label={t("f_temperature")} hint="0–2">
              <input
                type="number"
                min="0"
                max="2"
                step="0.1"
                value={form.temperature}
                onChange={(e) => setField("temperature", e.target.value)}
              />
            </Field>
            <Field label={t("f_max_tokens")}>
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
              {busy === "preview" ? t("btn_preview_busy") : t("btn_preview")}
            </button>
            {busy === "generate" ? (
              <button type="button" className="btn btn-stop" onClick={onStop}>
                ⏹ {t("btn_stop")}
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-primary"
                onClick={onGenerate}
                disabled={busy !== null}
              >
                {t("btn_generate")}
              </button>
            )}
          </div>
        </section>

        {/* ── Результат ── */}
        <section className="card">
          <h2 className="card-title">{t("result_title")}</h2>
          {error && <div className="error">{error}</div>}
          {resultMeta && <div className="result-meta">{resultMeta}</div>}
          <div className="result">{result || t("result_placeholder")}</div>
          {result && (
            <button type="button" className="btn btn-copy" onClick={onCopy}>
              {copied ? t("btn_copied") : t("btn_copy")}
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
