from django.db import models

from apps.orchestrator.models import Client


class EmailAccount(models.Model):
    """OAuth-linked mailbox. Never store a password here — only provider tokens."""

    class Provider(models.TextChoices):
        GMAIL = "gmail", "Gmail"
        OUTLOOK = "outlook", "Outlook"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="email_accounts")
    provider = models.CharField(max_length=16, choices=Provider.choices)
    email_address = models.EmailField()
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_expiry = models.DateTimeField(null=True, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["client", "email_address"]

    def __str__(self) -> str:
        return self.email_address
