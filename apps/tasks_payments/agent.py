"""Task & Payment tracker agent.

Phase 1: no bank/payment-system access — only what the client types in,
parsed by the orchestrator's LLM router into structured fields.
"""
from datetime import date, datetime

from apps.orchestrator.models import Client

from .models import Payment, Task


def _parse_due_date(due_date: str | None) -> date | None:
    if not due_date:
        return None
    try:
        return datetime.strptime(due_date, "%Y-%m-%d").date()
    except ValueError:
        return None


def handle_message(
    telegram_user_id: int,
    text: str,
    kind: str | None = None,
    counterparty: str | None = None,
    amount: float | None = None,
    currency: str = "UZS",
    title: str | None = None,
    due_date: str | None = None,
    note: str | None = None,
) -> str:
    client, _ = Client.objects.get_or_create(telegram_user_id=telegram_user_id)

    if kind == "payment" and counterparty and amount:
        parsed_due = _parse_due_date(due_date) or date.today()
        payment = Payment.objects.create(
            client=client,
            counterparty=counterparty,
            amount=amount,
            currency=currency,
            due_date=parsed_due,
            note=note or "",
        )
        return f"Записал платёж: {payment}"

    if kind == "task" and title:
        task = Task.objects.create(
            client=client,
            title=title,
            due_date=_parse_due_date(due_date),
        )
        return f"Записал задачу: {task.title}" + (f" (срок: {task.due_date})" if task.due_date else "")

    return (
        "Не хватило деталей, чтобы записать платёж или задачу. "
        "Уточните, пожалуйста, сумму/контрагента (для платежа) или "
        "название задачи."
    )
