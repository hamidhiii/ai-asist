import sys
import threading

from django.apps import AppConfig


class TelegramBotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.telegram_bot"

    def ready(self) -> None:
        # Download/load the whisper model in the background so the first real
        # voice message doesn't pay that cost inline and risk a gunicorn
        # worker timeout while Hugging Face is being fetched. Only do this
        # under the actual app server — not for manage.py test/migrate/etc,
        # where it would just waste a download.
        if "gunicorn" not in sys.argv[0]:
            return

        from .transcription import _model

        threading.Thread(target=_model, daemon=True).start()
