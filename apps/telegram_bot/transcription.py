"""Speech-to-text for Telegram voice messages via the Groq API (hosted Whisper).

Clients speak Russian or Uzbek. Whisper's open-ended language auto-detect is
unreliable on short Uzbek audio (it has answered Persian), so we only let it
choose between these two: trust a detection that already lands on ru/uz,
otherwise transcribe under each and keep the one the model scores higher.
"""
from django.conf import settings
from groq import Groq

# Whisper reports the detected language by name in verbose_json.
SUPPORTED_LANGUAGES = {"ru": "russian", "uz": "uzbek"}


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _request(client: Groq, file_path: str, language: str | None = None):
    kwargs = {"model": settings.GROQ_WHISPER_MODEL, "response_format": "verbose_json"}
    if language:
        kwargs["language"] = language
    with open(file_path, "rb") as audio_file:
        return client.audio.transcriptions.create(file=audio_file, **kwargs)


def _text(result) -> str:
    return (_get(result, "text") or "").strip()


def _score(result) -> float:
    scores = [
        _get(segment, "avg_logprob")
        for segment in (_get(result, "segments") or [])
        if _get(segment, "avg_logprob") is not None
    ]
    return sum(scores) / len(scores) if scores else float("-inf")


def transcribe(file_path: str) -> str:
    client = Groq(api_key=settings.GROQ_API_KEY)

    if settings.WHISPER_LANGUAGE:
        return _text(_request(client, file_path, settings.WHISPER_LANGUAGE))

    first = _request(client, file_path)
    detected = (_get(first, "language") or "").lower()
    if detected in SUPPORTED_LANGUAGES or detected in SUPPORTED_LANGUAGES.values():
        return _text(first)

    best_text, best_score = "", float("-inf")
    for code in SUPPORTED_LANGUAGES:
        result = _request(client, file_path, code)
        score = _score(result)
        if not best_text or score > best_score:
            best_text, best_score = _text(result), score
    return best_text
