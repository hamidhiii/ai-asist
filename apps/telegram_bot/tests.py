import json
from unittest.mock import AsyncMock, patch

from django.test import TestCase, override_settings

from apps.orchestrator.router import RoutedMessage


def _voice_update(chat_id: int = 555) -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 1700000000,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": chat_id, "is_bot": False, "first_name": "Test"},
            "voice": {"file_id": "voice123", "file_unique_id": "uniq1", "duration": 3},
        },
    }


@override_settings(TELEGRAM_WEBHOOK_SECRET="test-secret")
class VoiceMessageWebhookTests(TestCase):
    @patch("apps.telegram_bot.views._download_file", new_callable=AsyncMock)
    @patch("apps.telegram_bot.views.route_message")
    @patch("apps.telegram_bot.views.send_telegram_message")
    @patch("apps.telegram_bot.views.transcribe")
    def test_voice_message_is_transcribed_and_routed(
        self, mock_transcribe, mock_send, mock_route, mock_download
    ):
        mock_download.return_value = b"fake-ogg-bytes"
        mock_transcribe.return_value = "Привет"
        mock_route.return_value = RoutedMessage(agent_key="orchestrator", reply="Чем помочь?")

        response = self.client.post(
            "/telegram/webhook/",
            data=json.dumps(_voice_update()),
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="test-secret",
        )

        self.assertEqual(response.status_code, 204)
        mock_transcribe.assert_called_once()
        mock_route.assert_called_once_with(555, "Привет")
        mock_send.assert_called_once()
        sent_chat_id, sent_text = mock_send.call_args[0]
        self.assertEqual(sent_chat_id, 555)
        self.assertIn("Привет", sent_text)
        self.assertIn("Чем помочь?", sent_text)

    @patch("apps.telegram_bot.views._download_file", new_callable=AsyncMock)
    @patch("apps.telegram_bot.views.route_message")
    @patch("apps.telegram_bot.views.send_telegram_message")
    @patch("apps.telegram_bot.views.transcribe")
    def test_unintelligible_voice_message_skips_routing(
        self, mock_transcribe, mock_send, mock_route, mock_download
    ):
        mock_download.return_value = b"fake-ogg-bytes"
        mock_transcribe.return_value = ""

        response = self.client.post(
            "/telegram/webhook/",
            data=json.dumps(_voice_update()),
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="test-secret",
        )

        self.assertEqual(response.status_code, 204)
        mock_route.assert_not_called()
        mock_send.assert_called_once()

    def test_missing_secret_header_is_forbidden(self):
        response = self.client.post(
            "/telegram/webhook/",
            data=json.dumps(_voice_update()),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
