# Рыбацкий Трофей — Telegram bot MVP

Telegram-бот, который принимает фотографию с рыбалки и через OpenAI GPT Image 1.5 добавляет реалистичный трофей.

## MVP
- Long polling Telegram.
- Пользователь отправляет фото.
- Бот без дополнительных вопросов выбирает рыбу из 10 видов.
- Бот старается выбрать наиболее подходящего человека на фото.
- GPT Image 1.5, quality=low, 1024x1024.
- Результат возвращается в Telegram.

## Локальный запуск

1. Создайте виртуальное окружение и установите зависимости:
   `pip install -r requirements.txt`
2. Скопируйте `.env.example` в `.env`.
3. Заполните `TELEGRAM_BOT_TOKEN` и `OPENAI_API_KEY`.
4. Запустите: `python bot.py`

Ключи не коммитить и не отправлять в чат.

## Render / webhook

На Render бот работает через webhook. Переменные окружения:
- `BOT_MODE=webhook`
- `PUBLIC_BASE_URL=https://<имя-сервиса>.onrender.com`
- `WEBHOOK_SECRET=<длинная случайная строка>`
- `TELEGRAM_BOT_TOKEN=<токен BotFather>`
- `OPENAI_API_KEY=<ключ OpenAI>`

Render автоматически передаёт `PORT`. Endpoint проверки: `/health`.

Для локальной разработки можно оставить `BOT_MODE=polling`; при старте polling бот удаляет старый webhook, чтобы режимы не конфликтовали.
