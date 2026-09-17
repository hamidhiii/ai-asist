# ai-asist

Личный ассистент в Telegram на Django + Claude: маршрутизатор распределяет
сообщения клиента между тремя агентами.

## Агенты

- **tasks_payments** — учёт платежей и задач, дедлайны, напоминания через Celery Beat.
- **excel** — приём `.xlsx`/`.csv` из Telegram, разбор через pandas, сводка по листам.
- **email** — Gmail через OAuth2: чтение непрочитанных, черновик ответа через Claude,
  отправка только после явного подтверждения клиентом. Токены хранятся в БД
  зашифрованными (Fernet).

Голосовые сообщения в Telegram распознаются локально через `faster-whisper`
(без внешнего API) и обрабатываются как обычный текст — бот отвечает и
присылает, что именно распознал, чтобы клиент мог проверить/поправить.

Маршрутизация сообщений между агентами выполняется Claude через tool use
(`apps/orchestrator/router.py`).

## Стек

Django 5, DRF, PostgreSQL, Redis, Celery (+ Celery Beat), aiogram (Telegram),
Google API client (Gmail), Anthropic SDK.

## Быстрый старт (Docker)

1. Скопировать `.env.example` в `.env` и заполнить значения (см. ниже).
2. Поднять всё одной командой:

   ```bash
   docker compose up -d --build
   ```

   Поднимаются: `postgres`, `redis`, `web` (Django + gunicorn, применяет
   миграции при старте), `worker` и `beat` (Celery — напоминания и просроченные
   платежи по расписанию 09:00).

3. Создать суперпользователя (для `/admin/`):

   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

## Переменные окружения (`.env`)

| Переменная | Назначение |
|---|---|
| `DJANGO_SECRET_KEY` | Секретный ключ Django. Сгенерировать: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | `0` в продакшене |
| `DJANGO_ALLOWED_HOSTS` | Домен(ы) через запятую |
| `DATABASE_URL` | Строка подключения к Postgres |
| `REDIS_URL` | Строка подключения к Redis (брокер Celery) |
| `FIELD_ENCRYPTION_KEY` | Ключ шифрования Gmail-токенов. Сгенерировать: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. **Обязателен** — без него email-агент не запустится. Потеря ключа = потеря доступа ко всем сохранённым почтовым аккаунтам (клиентам придётся переподключить Gmail). |
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Секрет для проверки заголовка `X-Telegram-Bot-Api-Secret-Token` |
| `TELEGRAM_WEBHOOK_URL` | Публичный HTTPS-URL вебхука, напр. `https://your-domain.example/telegram/webhook/` |
| `ANTHROPIC_API_KEY` | Ключ Anthropic API |
| `ANTHROPIC_MODEL` | Модель роутера (по умолчанию `claude-sonnet-5`) |
| `WHISPER_MODEL_SIZE` | Размер модели faster-whisper для распознавания голосовых (`tiny`/`base`/`small`/`medium`/`large-v3`; по умолчанию `small` — баланс скорости и качества на CPU) |
| `WHISPER_LANGUAGE` | Код языка для распознавания (напр. `ru`); пусто — автоопределение на каждое сообщение (нужно для смешанной русской/узбекской аудитории) |
| `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` | Из Google Cloud Console (OAuth Consent Screen + Gmail API) |
| `GOOGLE_OAUTH_REDIRECT_URI` | `https://your-domain.example/email/oauth/callback/`, должен совпадать с настройками в Google Cloud Console |

## Регистрация Telegram-вебхука

После деплоя на публичный HTTPS-домен:

```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=$TELEGRAM_WEBHOOK_URL" \
  -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
```

## Тесты

```bash
docker compose exec web python manage.py test
```

Или локально без Docker (нужен доступ к Postgres из `DATABASE_URL`):

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py test
```

CI (`.github/workflows/ci.yml`) гоняет миграции, тесты и `manage.py check`
на каждый push/PR в `main`.

## Распознавание голоса

Модель faster-whisper скачивается автоматически при первом голосовом сообщении
(нужен доступ в интернет с сервера) и кэшируется в volume `whisper_cache`, чтобы
не перекачивать её при каждом пересборке образа. Модель `small` — это около
500 МБ и заметная нагрузка на CPU на первом запуске; если сервер слабый или
голосовых будет много одновременно, переключитесь на `base` или `tiny` через
`WHISPER_MODEL_SIZE`.

## Известные ограничения перед боевым запуском

- Модуль `tasks_payments` пока не подключён ни к одному банку/платёжной
  системе — все записи создаются только из текста, который парсит LLM.
- Нет rate-limiting на вебхуках (Telegram/Gmail OAuth callback).
- `DJANGO_DEBUG=1` и значения-заглушки в `.env.example` — обязательно
  заменить перед продакшеном.
