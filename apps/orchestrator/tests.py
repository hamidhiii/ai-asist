from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.orchestrator.router import route_message
from apps.tasks_payments.models import Payment


def _tool_use_response(tool_name: str, tool_input: dict):
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    response = MagicMock()
    response.content = [block]
    return response


def _text_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


class RouteMessageTests(TestCase):
    @patch("apps.orchestrator.router.anthropic.Anthropic")
    def test_payment_message_routes_to_tasks_payments_agent(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _tool_use_response(
            "tasks_payments",
            {
                "kind": "payment",
                "counterparty": "ООО Ромашка",
                "amount": 100,
                "due_date": "2026-09-01",
            },
        )
        mock_anthropic_cls.return_value = mock_client

        routed = route_message(111, "Заплатил Ромашке 100, срок 2026-09-01")

        self.assertEqual(routed.agent_key, "tasks_payments")
        self.assertTrue(Payment.objects.filter(counterparty="ООО Ромашка").exists())

    @patch("apps.orchestrator.router.anthropic.Anthropic")
    def test_excel_message_routes_to_excel_agent(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _tool_use_response("excel", {})
        mock_anthropic_cls.return_value = mock_client

        routed = route_message(112, "Разбери мою таблицу")

        self.assertEqual(routed.agent_key, "excel")
        self.assertIn("xlsx", routed.reply.lower())

    @patch("apps.orchestrator.router.anthropic.Anthropic")
    def test_email_message_routes_to_email_agent(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _tool_use_response(
            "email", {"intent": "check_inbox"}
        )
        mock_anthropic_cls.return_value = mock_client

        routed = route_message(113, "Проверь почту")

        self.assertEqual(routed.agent_key, "email")

    @patch("apps.orchestrator.router.anthropic.Anthropic")
    def test_general_question_returns_text_without_agent(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _text_response("Просто ответ")
        mock_anthropic_cls.return_value = mock_client

        routed = route_message(114, "Какая сегодня погода?")

        self.assertEqual(routed.agent_key, "orchestrator")
        self.assertEqual(routed.reply, "Просто ответ")
