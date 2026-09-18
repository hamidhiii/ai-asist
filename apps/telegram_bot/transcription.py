"""Speech-to-text for Telegram voice messages via a local faster-whisper model.

Runs on CPU. The model is loaded once per worker process (see apps.py, which
prewarms it in the background on startup) and reused for every call after.
"""
from functools import lru_cache

from django.conf import settings
from faster_whisper import WhisperModel

# Clients speak either Russian or Uzbek. Whisper's free-form language
# auto-detect is unreliable on short, code-switched phrases — it has
# misdetected clearly ru/uz audio as French — so we only ever let it pick
# between these two instead of trusting the open-ended guess.
SUPPORTED_LANGUAGES = ("ru", "uz")
CONFIDENCE_THRESHOLD = 0.6


@lru_cache(maxsize=1)
def _model() -> WhisperModel:
    return WhisperModel(settings.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")


def _join(segments) -> str:
    return " ".join(segment.text.strip() for segment in segments).strip()


def _avg_logprob(segments: list) -> float:
    return sum(s.avg_logprob for s in segments) / len(segments) if segments else float("-inf")


def transcribe(file_path: str) -> str:
    forced = settings.WHISPER_LANGUAGE
    model = _model()

    if forced:
        segments, _ = model.transcribe(file_path, language=forced)
        return _join(segments)

    segments, info = model.transcribe(file_path, language=None)
    segments = list(segments)

    if info.language in SUPPORTED_LANGUAGES and info.language_probability >= CONFIDENCE_THRESHOLD:
        return _join(segments)

    # Auto-detect landed outside ru/uz, or wasn't confident — re-run forced to
    # each supported language and keep whichever Whisper itself scores higher.
    best_text = _join(segments) if info.language in SUPPORTED_LANGUAGES else ""
    best_score = _avg_logprob(segments) if info.language in SUPPORTED_LANGUAGES else float("-inf")

    for lang in SUPPORTED_LANGUAGES:
        if lang == info.language:
            continue
        lang_segments, _ = model.transcribe(file_path, language=lang)
        lang_segments = list(lang_segments)
        score = _avg_logprob(lang_segments)
        if score > best_score:
            best_score = score
            best_text = _join(lang_segments)

    return best_text
