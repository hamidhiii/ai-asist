"""Task & Payment tracker agent.

Phase 1: no bank/payment-system access — only what the client types in.
This module is deliberately a thin façade so the orchestrator can call it
without knowing about models/ORM details.
"""
from apps.orchestrator.models import Client


def handle_message(telegram_user_id: int, text: str) -> str:
    Client.objects.get_or_create(telegram_user_id=telegram_user_id)
    # TODO: parse `text` into a Task/Payment via an LLM call, then persist it.
    return (
        "Записал. Пока разбор текста в задачу/платёж — заглушка; "
        "подключим LLM-парсер в следующей итерации."
    )
