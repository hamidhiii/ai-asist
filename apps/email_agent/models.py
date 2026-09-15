from django.db import models

from apps.orchestrator.models import Client

from .fields import EncryptedTextField


class EmailAccount(models.Model):
    """OAuth-linked mailbox. Never store a password here — only provider tokens."""

    class Provider(models.TextChoices):
        GMAIL = "gmail", "Gmail"
        OUTLOOK = "outlook", "Outlook"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="email_accounts")
    provider = models.CharField(max_length=16, choices=Provider.choices)
    email_address = models.EmailField()
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField()
    token_expiry = models.DateTimeField(null=True, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)

    last_unread_ids = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ["client", "email_address"]

    def __str__(self) -> str:
        return self.email_address


class EmailDraft(models.Model):
    """A reply drafted by the agent, awaiting the client's explicit confirmation."""

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="email_drafts")
    email_account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name="drafts")
    gmail_message_id = models.CharField(max_length=255)
    gmail_thread_id = models.CharField(max_length=255)
    to_address = models.EmailField()
    subject = models.CharField(max_length=998, blank=True)
    body = models.TextField()
    sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"draft to {self.to_address} ({'sent' if self.sent else 'pending'})"
