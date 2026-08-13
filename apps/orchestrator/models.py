from django.db import models


class Client(models.Model):
    """A single phase-1 assistant user, identified by their Telegram id."""

    telegram_user_id = models.BigIntegerField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.full_name or str(self.telegram_user_id)
