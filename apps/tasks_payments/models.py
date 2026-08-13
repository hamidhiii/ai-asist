from django.db import models

from apps.orchestrator.models import Client


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        PAID = "paid", "Оплачено"
        OVERDUE = "overdue", "Просрочено"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="payments")
    counterparty = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="UZS")
    due_date = models.DateField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date"]

    def __str__(self) -> str:
        return f"{self.counterparty} — {self.amount} {self.currency} ({self.due_date})"


class Task(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Открыта"
        DONE = "done", "Выполнена"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date"]

    def __str__(self) -> str:
        return self.title


class Reminder(models.Model):
    """A scheduled nudge for a Task or Payment, sent by Celery beat."""

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="reminders")
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True, related_name="reminders")
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name="reminders")
    remind_at = models.DateTimeField()
    sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["remind_at"]
