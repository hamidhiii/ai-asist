import asyncio

from aiogram import Bot
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Registers the Django webhook URL with Telegram (run once per deploy of a new URL)."

    def handle(self, *args, **options):
        async def _set():
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            try:
                await bot.set_webhook(
                    url=settings.TELEGRAM_WEBHOOK_URL,
                    secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
                )
            finally:
                await bot.session.close()

        asyncio.run(_set())
        self.stdout.write(self.style.SUCCESS(f"Webhook set to {settings.TELEGRAM_WEBHOOK_URL}"))
