from celery import shared_task
from django.utils import timezone

from apps.telegram_bot.client import send_telegram_message

from .models import Reminder


@shared_task
def send_due_reminders() -> int:
    """Runs on a Celery-beat schedule; sends any reminder whose time has come."""
    due = Reminder.objects.filter(sent=False, remind_at__lte=timezone.now()).select_related(
        "client", "payment", "task"
    )
    sent_count = 0
    for reminder in due:
        subject = reminder.payment or reminder.task
        send_telegram_message(reminder.client.telegram_user_id, f"Напоминание: {subject}")
        reminder.sent = True
        reminder.save(update_fields=["sent"])
        sent_count += 1
    return sent_count


@shared_task
def flag_overdue_payments() -> int:
    from .models import Payment

    overdue = Payment.objects.filter(status=Payment.Status.PENDING, due_date__lt=timezone.now().date())
    return overdue.update(status=Payment.Status.OVERDUE)
