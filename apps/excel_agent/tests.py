from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.excel_agent.models import ExcelUpload


class ExcelUploadWebhookTests(TestCase):
    @patch("apps.telegram_bot.views.analyze_upload", return_value="summary text")
    @patch("apps.telegram_bot.views.asyncio.run", return_value=b"fake-file-bytes")
    def test_handle_document_creates_excel_upload(self, mock_run, mock_analyze):
        from apps.telegram_bot.views import _handle_document

        document = MagicMock()
        document.file_name = "report.xlsx"

        reply = _handle_document(telegram_user_id=999, document=document)

        self.assertEqual(reply, "summary text")
        upload = ExcelUpload.objects.get()
        self.assertEqual(upload.original_name, "report.xlsx")
        self.assertEqual(upload.client.telegram_user_id, 999)
        mock_analyze.assert_called_once()
