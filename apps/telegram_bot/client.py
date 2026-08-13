import asyncio

from aiogram import Bot
from django.conf import settings


async def _send(chat_id: int, text: str) -> None:
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    finally:
        await bot.session.close()


def send_telegram_message(chat_id: int, text: str) -> None:
    """Sync wrapper so Celery tasks and Django views can call this directly."""
    asyncio.run(_send(chat_id, text))
