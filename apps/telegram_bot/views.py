import asyncio
import json
import logging
import tempfile

from aiogram import Bot, types
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.excel_agent.agent import analyze_upload
from apps.excel_agent.models import ExcelUpload
from apps.orchestrator.models import Client
from apps.orchestrator.router import route_message

from .client import send_telegram_message
from .transcription import transcribe

logger = logging.getLogger(__name__)


async def _download_file(file_id: str) -> bytes:
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        file = await bot.get_file(file_id)
        buffer = await bot.download_file(file.file_path)
        return buffer.read()
    finally:
        await bot.session.close()


def _handle_document(telegram_user_id: int, document: types.Document) -> str:
    client, _ = Client.objects.get_or_create(telegram_user_id=telegram_user_id)
    content = asyncio.run(_download_file(document.file_id))
    upload = ExcelUpload.objects.create(client=client, original_name=document.file_name)
    upload.file.save(document.file_name, ContentFile(content))
    return analyze_upload(upload)


def _handle_voice(telegram_user_id: int, voice: types.Voice) -> str:
    try:
        content = asyncio.run(_download_file(voice.file_id))
        with tempfile.NamedTemporaryFile(suffix=".ogg") as tmp:
            tmp.write(content)
            tmp.flush()
            text = transcribe(tmp.name)
    except Exception:
        logger.exception("Voice message transcription failed")
        return "Не удалось обработать голосовое сообщение. Попробуйте ещё раз или напишите текстом."

    if not text:
        return "Не удалось разобрать голосовое сообщение. Попробуйте ещё раз или напишите текстом."

    routed = route_message(telegram_user_id, text)
    return f"Распознал: «{text}»\n\n{routed.reply}"


@csrf_exempt
@require_POST
def webhook(request: HttpRequest) -> HttpResponse:
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != settings.TELEGRAM_WEBHOOK_SECRET:
        return HttpResponseForbidden()

    update = types.Update.model_validate(json.loads(request.body))
    message = update.message
    if message is None:
        return HttpResponse(status=204)

    if message.document is not None:
        reply = _handle_document(message.from_user.id, message.document)
        send_telegram_message(message.chat.id, reply)
        return HttpResponse(status=204)

    if message.voice is not None:
        reply = _handle_voice(message.from_user.id, message.voice)
        send_telegram_message(message.chat.id, reply)
        return HttpResponse(status=204)

    if message.text is None:
        return HttpResponse(status=204)

    routed = route_message(message.from_user.id, message.text)
    send_telegram_message(message.chat.id, routed.reply)
    return HttpResponse(status=204)
