"""Speech-to-text for Telegram voice messages via a local faster-whisper model.

Runs on CPU. The model is loaded once per worker process (first voice message
pays the load cost) and reused for every call after that.
"""
from functools import lru_cache

from django.conf import settings
from faster_whisper import WhisperModel


@lru_cache(maxsize=1)
def _model() -> WhisperModel:
    return WhisperModel(settings.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")


def transcribe(file_path: str) -> str:
    segments, _ = _model().transcribe(file_path, language=settings.WHISPER_LANGUAGE or None)
    return " ".join(segment.text.strip() for segment in segments).strip()
