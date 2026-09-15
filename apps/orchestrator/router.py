"""Routes an incoming Telegram message to the agent responsible for it.

Uses Claude with tool use as the router: each agent is registered as a tool,
and the model picks exactly one per message (or answers directly for
general questions that don't belong to any agent).
"""
from dataclasses import dataclass
from typing import Callable

import anthropic
from django.conf import settings

from apps.email_agent.agent import handle_message as email_agent_handle
from apps.excel_agent.agent import handle_message as excel_agent_handle
from apps.tasks_payments.agent import handle_message as tasks_payments_handle

AgentHandler = Callable[..., str]

AGENTS: dict[str, AgentHandler] = {
    "tasks_payments": tasks_payments_handle,
    "excel": excel_agent_handle,
    "email": email_agent_handle,
}

SYSTEM_PROMPT = (
    "Ты — маршрутизатор личного ассистента. На каждое сообщение клиента "
    "вызови ровно один подходящий инструмент (агента). Если сообщение — "
    "общий вопрос, не относящийся ни к одному из агентов, ответь текстом "
    "напрямую, без вызова инструментов."
)

TOOLS = [
    {
        "name": "tasks_payments",
        "description": (
            "Учёт платежей и задач клиента: зафиксировать новый платёж или "
            "задачу, дедлайн, напоминание. Используй, когда речь о деньгах, "
            "оплате, долге, сроке или задаче."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["payment", "task"],
                    "description": "Тип записи: payment — платёж, task — задача.",
                },
                "counterparty": {
                    "type": "string",
                    "description": "Контрагент/получатель платежа (для payment).",
                },
                "amount": {
                    "type": "number",
                    "description": "Сумма платежа (для payment).",
                },
                "currency": {
                    "type": "string",
                    "description": "Валюта, например UZS, USD (для payment).",
                },
                "title": {
                    "type": "string",
                    "description": "Краткое название задачи (для task).",
                },
                "due_date": {
                    "type": "string",
                    "description": "Срок в формате YYYY-MM-DD, если указан.",
                },
                "note": {
                    "type": "string",
                    "description": "Произвольный комментарий.",
                },
            },
            "required": ["kind"],
        },
    },
    {
        "name": "excel",
        "description": (
            "Работа с Excel/CSV файлами: анализ загруженной таблицы, "
            "вопросы про столбцы/статистику. Используй, когда клиент "
            "спрашивает про таблицу, файл или просит прислать сводку."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {
                    "type": "string",
                    "description": "Уточнение запроса клиента, если есть.",
                }
            },
        },
    },
    {
        "name": "email",
        "description": (
            "Работа с почтой клиента: проверить входящие, составить "
            "черновик ответа, подтвердить или отменить отправку письма."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": ["check_inbox", "draft_reply", "confirm_send", "cancel"],
                    "description": "Что нужно сделать с почтой.",
                },
                "message_index": {
                    "type": "integer",
                    "description": "Номер письма из последнего списка непрочитанных, если указан клиентом.",
                },
                "instruction": {
                    "type": "string",
                    "description": "Инструкция клиента для черновика ответа.",
                },
            },
            "required": ["intent"],
        },
    },
]


@dataclass
class RoutedMessage:
    agent_key: str
    reply: str


def route_message(telegram_user_id: int, text: str) -> RoutedMessage:
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=[{"role": "user", "content": text}],
    )

    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use is not None:
        handler = AGENTS[tool_use.name]
        reply = handler(telegram_user_id, text, **tool_use.input)
        return RoutedMessage(agent_key=tool_use.name, reply=reply)

    text_block = next((b for b in response.content if b.type == "text"), None)
    reply = text_block.text if text_block is not None else "Не удалось обработать сообщение."
    return RoutedMessage(agent_key="orchestrator", reply=reply)
