"""Routes an incoming Telegram message to the agent responsible for it.

Uses Claude with tool use as the router: each agent is registered as a tool,
and the model picks exactly one per message (or answers directly for
general questions that don't belong to any agent).
"""
import logging
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
    "Ты — маршрутизатор личного ассистента. Если сообщение клиента касается "
    "платежей и задач, Excel-файлов или почты — вызови ровно один подходящий "
    "инструмент (агента). Если это общий вопрос, ответь сам; когда нужны "
    "актуальные данные из интернета (курсы валют, новости, погода, факты), "
    "воспользуйся веб-поиском и отвечай коротко. Отвечай на том языке, на "
    "котором написал клиент (русский или узбекский). Пиши обычным текстом "
    "без Markdown-разметки: Telegram её не отображает."
)

WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 3}
MAX_PAUSE_CONTINUATIONS = 3
TELEGRAM_MAX_LEN = 4000

logger = logging.getLogger(__name__)

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


def _create(client: anthropic.Anthropic, messages: list, with_web_search: bool):
    tools = [*TOOLS, WEB_SEARCH_TOOL] if with_web_search else TOOLS
    return client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        tools=tools,
        messages=messages,
    )


def _final_text(content: list) -> str:
    # With web search, the model narrates before searching ("Let me look...");
    # the actual answer is the text that comes after the last search result.
    last_result = max(
        (i for i, block in enumerate(content) if block.type == "web_search_tool_result"),
        default=-1,
    )
    texts = [b.text for b in content[last_result + 1 :] if b.type == "text"]
    if not texts:
        texts = [b.text for b in content if b.type == "text"]
    return "".join(texts).strip()


def route_message(telegram_user_id: int, text: str) -> RoutedMessage:
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    messages = [{"role": "user", "content": text}]
    with_web_search = True

    for _ in range(MAX_PAUSE_CONTINUATIONS + 1):
        try:
            response = _create(client, messages, with_web_search)
        except (anthropic.BadRequestError, anthropic.PermissionDeniedError):
            if not with_web_search:
                raise
            # Web search not enabled for this org/model: keep the bot working
            # for the three agents instead of failing every message.
            logger.exception("Web search request rejected; retrying without it")
            with_web_search = False
            continue

        if response.stop_reason != "pause_turn":
            break
        messages = [messages[0], {"role": "assistant", "content": response.content}]

    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use is not None:
        handler = AGENTS[tool_use.name]
        reply = handler(telegram_user_id, text, **tool_use.input)
        return RoutedMessage(agent_key=tool_use.name, reply=reply)

    reply = _final_text(response.content) or "Не удалось обработать сообщение."
    return RoutedMessage(agent_key="orchestrator", reply=reply[:TELEGRAM_MAX_LEN])
