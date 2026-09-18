import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase, override_settings

from apps.orchestrator.router import RoutedMessage
from apps.telegram_bot.transcription import transcribe


def _result(text: str, language: str, avg_logprob: float = -0.3):
    return SimpleNamespace(
        text=text, language=language, segments=[{"avg_logprob": avg_logprob}]
    )


@override_settings(GROQ_API_KEY="k", GROQ_WHISPER_MODEL="m", WHISPER_LANGUAGE="")
class TranscribeLanguageTests(TestCase):
    def _run(self, results):
        with patch("apps.telegram_bot.transcription.Groq") as groq_cls:
            create = groq_cls.return_value.audio.transcriptions.create
            create.side_effect = results
            with patch("builtins.open", MagicMock()):
                text = transcribe("voice.ogg")
        return text, create

    def test_detected_supported_language_is_used_directly(self):
        text, create = self._run([_result("привет", "russian")])
        self.assertEqual(text, "привет")
        self.assertEqual(create.call_count, 1)

    def test_unsupported_detection_retries_and_keeps_higher_score(self):
        text, create = self._run(
            [
                _result("متأسفم", "persian"),
                _result("привет мир", "russian", avg_logprob=-0.9),
                _result("salom dunyo", "uzbek", avg_logprob=-0.2),
            ]
        )
        self.assertEqual(text, "salom dunyo")
        self.assertEqual(create.call_count, 3)
        forced = [c.kwargs.get("language") for c in create.call_args_list]
        self.assertEqual(forced, [None, "ru", "uz"])

    @override_settings(WHISPER_LANGUAGE="uz")
    def test_forced_language_makes_single_call(self):
        text, create = self._run([_result("salom", "uzbek")])
        self.assertEqual(text, "salom")
        self.assertEqual(create.call_count, 1)
        self.assertEqual(create.call_args.kwargs["language"], "uz")


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

    @patch("apps.telegram_bot.views._download_file", new_callable=AsyncMock)
    @patch("apps.telegram_bot.views.route_message")
    @patch("apps.telegram_bot.views.send_telegram_message")
    @patch("apps.telegram_bot.views.transcribe")
    def test_transcription_error_replies_instead_of_staying_silent(
        self, mock_transcribe, mock_send, mock_route, mock_download
    ):
        mock_download.return_value = b"fake-ogg-bytes"
        mock_transcribe.side_effect = RuntimeError("groq unavailable")

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
