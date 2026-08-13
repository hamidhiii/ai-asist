"""Routes an incoming Telegram message to the agent responsible for it.

Phase 1 keeps this a plain keyword router. Swap `classify_intent` for an LLM
call later without touching the agents themselves.
"""
from dataclasses import dataclass
from typing import Callable

from apps.email_agent.agent import handle_message as email_agent_handle
from apps.excel_agent.agent import handle_message as excel_agent_handle
from apps.tasks_payments.agent import handle_message as tasks_payments_handle

AgentHandler = Callable[[int, str], str]

AGENTS: dict[str, AgentHandler] = {
    "tasks_payments": tasks_payments_handle,
    "excel": excel_agent_handle,
    "email": email_agent_handle,
}

_KEYWORDS = {
    "excel": ("excel", "таблиц", "xlsx", "csv"),
    "email": ("почт", "email", "gmail", "письмо", "outlook"),
    "tasks_payments": ("оплат", "плат", "задач", "напомни", "срок", "долг"),
}


@dataclass
class RoutedMessage:
    agent_key: str
    reply: str


def classify_intent(text: str) -> str:
    lowered = text.lower()
    for agent_key, keywords in _KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return agent_key
    return "tasks_payments"


def route_message(telegram_user_id: int, text: str) -> RoutedMessage:
    agent_key = classify_intent(text)
    handler = AGENTS[agent_key]
    reply = handler(telegram_user_id, text)
    return RoutedMessage(agent_key=agent_key, reply=reply)
