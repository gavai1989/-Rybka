from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message, KeyboardButton, ReplyKeyboardMarkup
from aiohttp import web
from dotenv import load_dotenv
from openai import OpenAI
from webhook import build_webhook_url
from web_server import create_web_app

from fish import choose_fish
from image_editor import edit_fishing_photo

PHOTO_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📸 Добавить трофей")]],
    resize_keyboard=True,
    is_persistent=True,
)

START_TEXT = """🎣 <b>РЫБАЦКИЙ ТРОФЕЙ AI</b>

Так набухался, что забыл сфоткаться с трофеем? 😎
<b>Не беда. Бывает.</b>

Отправь сюда фотографию с рыбалки — <b>AI добавит тебе достойный улов.</b> 🐟

Ничего выбирать не нужно.
Не надо объяснять, кто где стоит.
Просто отправь фото — остальное сделаем сами.

🔥 МАКСИМАЛЬНО РЕАЛИСТИЧНО:
— сохраним тебя и твоих друзей;
— сохраним фон и место рыбалки;
— подберём подходящую рыбу;
— аккуратно впишем её в фотографию.

В итоге — как будто ты действительно её поймал. 😉

📸 Отправляй фото. Пора возвращать рыбацкую репутацию!

РЫБАЦКИЙ ТРОФЕЙ AI
Больше чем фото — настоящая рыбацкая история. 🐟
"""

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_MODE = os.getenv("BOT_MODE", "polling").lower()
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
PORT = int(os.getenv("PORT", "10000"))

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")
if BOT_MODE not in {"polling", "webhook"}:
    raise RuntimeError("BOT_MODE must be polling or webhook")
if BOT_MODE == "webhook" and (not PUBLIC_BASE_URL or not WEBHOOK_SECRET):
    raise RuntimeError("PUBLIC_BASE_URL and WEBHOOK_SECRET are required in webhook mode")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()
openai_client = OpenAI(api_key=OPENAI_API_KEY)

@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(START_TEXT, parse_mode="HTML", reply_markup=PHOTO_KEYBOARD)


@router.message(F.text == "📸 Добавить трофей")
async def add_trophy_handler(message: Message) -> None:
    await message.answer("📸 Отлично. Просто отправь фотографию с рыбалки — я сам добавлю трофей.")


@router.message(F.photo)
async def photo_handler(message: Message, bot: Bot) -> None:
    status = await message.answer("🎣 Смотрю, кому здесь достался улов…")

    try:
        photo = message.photo[-1]
        telegram_file = await bot.get_file(photo.file_id)

        with tempfile.TemporaryDirectory(prefix="fishing-bot-") as temp_dir:
            input_path = Path(temp_dir) / "input.jpg"
            output_path = Path(temp_dir) / "result.png"
            await bot.download_file(telegram_file.file_path, destination=input_path)

            fish = choose_fish()
            result_bytes = await asyncio.to_thread(
                edit_fishing_photo, openai_client, input_path, fish
            )
            output_path.write_bytes(result_bytes)

            await message.answer_photo(
                photo=FSInputFile(output_path),
                caption="🎣 Готово. Трофей найден. Хорошая рыбалка 😎",
            )

    except Exception:
        logger.exception("Failed to process fishing photo")
        await message.answer(
            "Не получилось обработать фото 😕\n"
            "Попробуй отправить другое фото, где людей хорошо видно."
        )
    finally:
        try:
            await status.delete()
        except Exception:
            pass


@router.message()
async def fallback_handler(message: Message) -> None:
    await message.answer("📸 Отправь фотографию с рыбалки — остальное я сделаю сам.")


async def main() -> None:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    if BOT_MODE == "webhook":
        webhook_url = build_webhook_url(PUBLIC_BASE_URL, WEBHOOK_SECRET)
        await bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
        app = create_web_app(bot, dispatcher, WEBHOOK_SECRET)
        logger.info("Fishing bot started with webhook on port %s", PORT)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()
            await bot.delete_webhook()
            await bot.session.close()
        return

    await bot.delete_webhook(drop_pending_updates=False)
    logger.info("Fishing bot started with long polling")

    health_app = web.Application()
    async def health(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})
    health_app.router.add_get("/health", health)
    health_runner = web.AppRunner(health_app)
    await health_runner.setup()
    health_site = web.TCPSite(health_runner, "0.0.0.0", PORT)
    await health_site.start()
    logger.info("Health server started on port %s", PORT)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await health_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
