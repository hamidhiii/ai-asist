from unittest.mock import MagicMock, patch

import anthropic
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


def _block(block_type: str, **attrs):
    block = MagicMock()
    block.type = block_type
    for key, value in attrs.items():
        setattr(block, key, value)
    return block


def _response(blocks: list, stop_reason: str = "end_turn"):
    response = MagicMock()
    response.content = blocks
    response.stop_reason = stop_reason
    return response


class WebSearchRoutingTests(TestCase):
    @patch("apps.orchestrator.router.anthropic.Anthropic")
    def test_answer_after_web_search_skips_narration(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _response(
            [
                _block("text", text="Сейчас поищу."),
                _block("server_tool_use"),
                _block("web_search_tool_result"),
                _block("text", text="Курс доллара — 12 700 сум."),
            ]
        )
        mock_anthropic_cls.return_value = mock_client

        routed = route_message(201, "Какой курс доллара?")

        self.assertEqual(routed.agent_key, "orchestrator")
        self.assertEqual(routed.reply, "Курс доллара — 12 700 сум.")
        tools = mock_client.messages.create.call_args.kwargs["tools"]
        self.assertTrue(any(t.get("name") == "web_search" for t in tools))

    @patch("apps.orchestrator.router.anthropic.Anthropic")
    def test_pause_turn_is_continued(self, mock_anthropic_cls):
        paused = _response([_block("server_tool_use")], stop_reason="pause_turn")
        done = _response([_block("text", text="Готово")])
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [paused, done]
        mock_anthropic_cls.return_value = mock_client

        routed = route_message(202, "Что нового?")

        self.assertEqual(routed.reply, "Готово")
        self.assertEqual(mock_client.messages.create.call_count, 2)
        second_messages = mock_client.messages.create.call_args.kwargs["messages"]
        self.assertEqual(second_messages[-1]["role"], "assistant")

    @patch("apps.orchestrator.router.anthropic.Anthropic")
    def test_rejected_web_search_falls_back_to_agents_only(self, mock_anthropic_cls):
        rejected = anthropic.BadRequestError(
            "web search not enabled",
            response=MagicMock(status_code=400),
            body=None,
        )
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [rejected, _response([_block("text", text="Ок")])]
        mock_anthropic_cls.return_value = mock_client

        routed = route_message(203, "Привет")

        self.assertEqual(routed.reply, "Ок")
        retry_tools = mock_client.messages.create.call_args.kwargs["tools"]
        self.assertFalse(any(t.get("name") == "web_search" for t in retry_tools))

    @patch("apps.orchestrator.router.anthropic.Anthropic")
    def test_long_reply_is_truncated_for_telegram(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _response([_block("text", text="а" * 5000)])
        mock_anthropic_cls.return_value = mock_client

        routed = route_message(204, "Расскажи всё")

        self.assertEqual(len(routed.reply), 4000)
