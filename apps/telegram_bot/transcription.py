"""Speech-to-text for Telegram voice messages via the Groq API.

Groq hosts whisper-large-v3 on its own hardware behind an OpenAI-compatible
endpoint (free tier), so transcription runs off this server entirely — no
local model, no CPU/RAM cost here, and noticeably better accuracy than the
small local model we started with (especially for Uzbek and mixed ru/uz
audio).
"""
from django.conf import settings
from groq import Groq


def transcribe(file_path: str) -> str:
    client = Groq(api_key=settings.GROQ_API_KEY)
    kwargs = {"model": settings.GROQ_WHISPER_MODEL, "response_format": "text"}
    if settings.WHISPER_LANGUAGE:
        kwargs["language"] = settings.WHISPER_LANGUAGE

    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(file=audio_file, **kwargs)

    return str(transcription).strip()
