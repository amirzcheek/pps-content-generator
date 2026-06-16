# Развёртывание сервиса генератора учебного контента

Инструкция по «пути Б» под инфраструктуру KNUS.

## Раскладка инфраструктуры

```
[ Браузер ] → HTTPS → [ nginx (выделенный сервер, TLS, домен) ]
                              │  proxy_pass → 127.0.0.1:8080
                              ▼
                       [ web-сервер ]
                       content-gen (FastAPI/uvicorn, слушает только localhost)
                              │  LLM_BASE_URL
                              ▼
                       [ LLM-сервер ] (локальная модель 14b, OpenAI-совместимый API)
```

- Сервис **наружу не торчит** — слушает `127.0.0.1:8080`, снаружи доступен только через nginx.
- Первая версия — русский/английский (модель 14b). Казахский подключается позже
  (переменные `KAZ_*` пока пустые).
- n8n (Telegram-интерфейс) подключается позже — бэкенд при этом не меняется.

---

## 1. Настроить переменные окружения

На **web-сервере**, в каталоге проекта:

```bash
cp .env.example .env
nano .env
```

Заполните адрес и имя модели 14b (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`).
`KAZ_*` оставьте пустыми.

> При запуске через **Docker**, если LLM на том же хосте, укажите
> `LLM_BASE_URL=http://host.docker.internal:11434/v1` и раскомментируйте
> `extra_hosts` в `docker-compose.yml`.

---

## 2. Запустить сервис — Docker ИЛИ systemd

### Вариант A — Docker (рекомендуется)

```bash
docker compose up -d --build
docker compose ps
curl -s http://127.0.0.1:8080/health      # {"status":"ok"}
docker compose logs -f content-gen        # логи
```

Обновление после изменений: `docker compose up -d --build`.

### Вариант B — systemd (без Docker)

```bash
sudo mkdir -p /opt/content-gen
sudo cp -r backend /opt/content-gen/
sudo cp .env /opt/content-gen/.env
sudo python3 -m venv /opt/content-gen/.venv
sudo /opt/content-gen/.venv/bin/pip install -r /opt/content-gen/backend/requirements.txt
sudo chown -R www-data:www-data /opt/content-gen

sudo cp content-gen.service /etc/systemd/system/content-gen.service
sudo systemctl daemon-reload
sudo systemctl enable --now content-gen
systemctl status content-gen
curl -s http://127.0.0.1:8080/health
```

---

## 3. Тестовая страница

```bash
sudo mkdir -p /var/www/content-gen
sudo cp web/index.html /var/www/content-gen/index.html
```

Страница обращается к `/templates` и `/generate` на том же домене (same-origin),
поэтому отдельный CORS не нужен.

---

## 4. Сеть и фаервол (если nginx на отдельном сервере)

Когда nginx стоит на отдельном сервере, сервис должен слушать внутренний IP
web-сервера (а не только `127.0.0.1`), но порт 8080 должен быть закрыт для всех,
кроме nginx-хоста. В интернет порт не открывается.

1. В `.env` на web-сервере задать адрес прослушивания:
   ```bash
   BIND_IP=<внутренний IP web-сервера>      # для Docker
   BIND_HOST=<внутренний IP web-сервера>    # для systemd
   ```
   и перезапустить сервис (`docker compose up -d` или `systemctl restart content-gen`).

2. Закрыть порт 8080 фаерволом — доступ только с nginx-хоста (ufw):
   ```bash
   sudo ufw allow from <IP nginx-сервера> to any port 8080 proto tcp
   sudo ufw deny 8080
   ```
   Проверка с nginx-сервера: `curl http://<внутренний IP web-сервера>:8080/health`.

> Если nginx на ТОМ ЖЕ хосте, что и сервис — этот шаг не нужен:
> оставьте `BIND_IP=127.0.0.1` и `upstream { server 127.0.0.1:8080; }`.

## 5. nginx + TLS

На **выделенном nginx-сервере**:

```bash
sudo cp nginx/content-gen.conf /etc/nginx/sites-available/content-gen.conf
sudo ln -s /etc/nginx/sites-available/content-gen.conf /etc/nginx/sites-enabled/
# Если nginx на отдельной машине — в content-gen.conf заменить 127.0.0.1:8080
# в upstream на внутренний адрес web-сервера.
sudo nginx -t          # проверка конфигурации
```

### Сертификат — certbot (Let's Encrypt)

```bash
sudo certbot --nginx -d content.ai.knus.edu.kz
```

### ИЛИ готовый wildcard `*.ai.knus.edu.kz`

Положите файлы сертификата на сервер и в `content-gen.conf` закомментируйте
строки Let's Encrypt, раскомментировав блок wildcard (`ssl_certificate*`).

### Применить

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 6. Проверка снаружи

1. В браузере открыть `https://content.ai.knus.edu.kz/` — должна открыться тестовая страница.
2. Выбрать тип, заполнить дисциплину и тему, нажать «Сгенерировать» — должен прийти
   ответ с метаданными (модель, язык).
3. Проверка API напрямую:
   ```bash
   curl https://content.ai.knus.edu.kz/templates
   ```

---

## Что дальше

- **Доводка `templates.json`** — методисты правят формулировки промптов без кода
  (в Docker — пересборка образа; в systemd — правка `/opt/content-gen/backend/templates.json`
  и `systemctl restart content-gen`).
- **Казахский язык** — когда появится KazLLM/Sherkala, заполнить `KAZ_BASE_URL`/`KAZ_MODEL`
  в `.env` и перезапустить сервис (маршрутизация по языку уже в коде).
- **Telegram через n8n** — нода HTTP Request шлёт `POST /generate` на тот же сервис;
  бэкенд не меняется.
- **Экспорт в .docx** — отдельный шаг постобработки ответа (на стороне фронтенда/n8n).

## Безопасность

- Сервис слушает только `127.0.0.1:8080` — снаружи недоступен, весь трафик идёт через nginx с TLS.
- Персональные данные не обрабатываются; генерация — на локальных моделях внутри сети вуза.
- При необходимости ограничить доступ к тестовой странице — basic-auth в nginx:
  ```bash
  sudo apt-get install apache2-utils
  sudo htpasswd -c /etc/nginx/.htpasswd content
  ```
  и в `location / { ... }` файла `content-gen.conf` добавить:
  ```nginx
  auth_basic "KNUS content-gen";
  auth_basic_user_file /etc/nginx/.htpasswd;
  ```
