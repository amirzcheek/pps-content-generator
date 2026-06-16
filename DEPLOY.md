# Развёртывание агента на портале ai.knus.edu.kz

Агент подключается под-путём основного домена — `https://ai.knus.edu.kz/agents/course-dev-content-generator/`
(как `course-dev`, `examination` и т.д.), **единым сервисом**: FastAPI отдаёт и
React-интерфейс, и API.

## Раскладка инфраструктуры

```
[ Браузер ] → HTTPS → [ nginx основного домена (10.99.99.10, TLS портала) ]
                          │  location /agents/course-dev-content-generator/
                          │  proxy_pass → web-сервер:8080  (префикс обрезается)
                          ▼
                   [ web-сервер (10.99.99.150) ]
                   content-gen: FastAPI/uvicorn (React + API в одном сервисе)
                          │  LLM_BASE_URL
                          ▼
                   [ LLM-шлюз (10.99.99.201) ] — gemini-3.1-flash-lite (OpenAI-совместимый)
```

- Сервис **не торчит в интернет** — слушает внутренний адрес web-сервера, порт 8080
  закрыт фаерволом для всех, кроме nginx-хоста.
- TLS и домен — уже на nginx-сервере портала; **отдельный сертификат не нужен**,
  добавляется только `location`-блок.
- Модель — `gemini-3.1-flash-lite` (дешёвая, мультиязычна). Имя модели всегда
  передаётся явно, иначе шлюз берёт дорогую. Казахский идёт на тот же шлюз.
- n8n (Telegram) подключается позже к тому же `/generate` — бэкенд не меняется.

> **Slug агента** — `course-dev-content-generator`. Он встречается в трёх местах и
> должен совпадать: `ROOT_PATH` и `VITE_BASE/VITE_API_BASE` (сборка) и `location` в nginx.

---

## 1. Код и переменные окружения (web-сервер 10.99.99.150)

```bash
git clone https://github.com/amirzcheek/pps-content-generator.git
cd pps-content-generator
cp .env.example .env
nano .env
```

Заполнить в `.env`:
```ini
LLM_BASE_URL=http://10.99.99.201:<порт>/v1     # адрес LLM-шлюза
LLM_MODEL=gemini-3.1-flash-lite                 # дешёвая модель, указывать явно!
LLM_API_KEY=<ключ шлюза>                         # для Gemini — реальный ключ
KAZ_BASE_URL=                                    # пусто -> kk идёт на тот же шлюз
KAZ_MODEL=
KAZ_API_KEY=

ROOT_PATH=/agents/course-dev-content-generator  # под-путь портала
BIND_IP=10.99.99.150                            # слушаем внутренний IP (nginx отдельно)
BIND_HOST=10.99.99.150
```

> Docker + LLM на том же хосте — используйте `host.docker.internal` в `LLM_BASE_URL`
> и раскомментируйте `extra_hosts` в `docker-compose.yml`.

---

## 2. Запустить сервис — Docker ИЛИ systemd

### Вариант A — Docker (рекомендуется)

Сборка соберёт React (под под-путь) и упакует вместе с FastAPI:

```bash
docker compose up -d --build
curl http://10.99.99.150:8080/health      # {"status":"ok"}
```

> Если slug другой — переопределите при сборке:
> `VITE_BASE=/agents/<slug>/ VITE_API_BASE=/agents/<slug> docker compose up -d --build`
> и поставьте такой же `ROOT_PATH` в `.env`.

### Вариант B — systemd (без Docker)

Шаги (включая сборку фронтенда) — в комментариях файла `content-gen.service`.
Кратко: собрать `frontend` с `VITE_BASE/VITE_API_BASE`, положить `dist` в
`/opt/content-gen/backend/static`, создать venv, включить юнит.

---

## 3. Фаервол (порт 8080 только для nginx-хоста)

На web-сервере:
```bash
sudo ufw allow from 10.99.99.10 to any port 8080 proto tcp
sudo ufw deny 8080
```
Проверка с nginx-сервера: `curl http://10.99.99.150:8080/health`.

---

## 4. nginx — подключить под-путь (nginx-сервер 10.99.99.10)

В конфиге **основного домена** `ai.knus.edu.kz` (внутри существующего
`server { listen 443 ssl; ... }`) добавить содержимое
[`nginx/agent-location.conf`](nginx/agent-location.conf):

```nginx
location /agents/course-dev-content-generator/ {
    proxy_pass http://10.99.99.150:8080/;     # внутренний IP web-сервера, со слешем!
    proxy_http_version 1.1;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Prefix /agents/course-dev-content-generator;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}
location = /agents/course-dev-content-generator {
    return 301 /agents/course-dev-content-generator/;
}
```

Слеш в `proxy_pass http://...:8080/;` **обрезает** префикс — сервис видит у себя
`/`, `/templates`, `/assets/...`. Применить:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

> Если в портале принято НЕ обрезать префикс — уберите слеш после `:8080`
> (`proxy_pass http://10.99.99.150:8080;`); `ROOT_PATH` уже выставлен и всё совпадёт.

---

## 5. Добавить карточку агента на портал

В реестре агентов портала добавить ссылку на
`/agents/course-dev-content-generator/` (как для course-dev и др.) — по вашему
механизму портала.

---

## 6. Проверка снаружи

1. Открыть `https://ai.knus.edu.kz/agents/course-dev-content-generator/` — должен
   загрузиться интерфейс (навбар, список типов).
2. Выбрать тип, заполнить дисциплину/тему, нажать «Сгенерировать».
3. API напрямую:
   ```bash
   curl https://ai.knus.edu.kz/agents/course-dev-content-generator/templates
   ```

---

## Что дальше

- **Доводка `templates.json`** — методисты правят промпты (Docker — пересборка
  образа; systemd — правка `backend/templates.json` + `systemctl restart content-gen`).
- **Казахский** — заполнить `KAZ_*` в `.env` и перезапустить (маршрутизация уже в коде).
- **Telegram через n8n** — нода HTTP Request шлёт `POST .../generate`; бэкенд не меняется.
- **Экспорт в .docx** — постобработка ответа (фронтенд/n8n).

## Безопасность

- Сервис слушает только внутренний адрес; порт 8080 закрыт фаерволом — наружу только
  через nginx с TLS.
- Персональные данные не обрабатываются; генерация — на локальных моделях вуза.
- Роль/админка в навбаре берутся из сессии портала (`/api/auth/session`) — см.
  `frontend/src/auth/useSession.js`.

## Прочее

- [`nginx/content-gen.conf`](nginx/content-gen.conf) — альтернатива: отдельный
  поддомен `content.ai.knus.edu.kz` (если когда-то понадобится вне портала).
- [`web/index.html`](web/index.html) — простая диагностическая страница (vanilla JS),
  не используется при интеграции в портал; React-интерфейс отдаёт сам сервис.
