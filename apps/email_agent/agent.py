"""Email agent: reads Gmail, drafts replies with Claude, and sends only on
explicit client confirmation in a separate Telegram message.
"""
import base64
from email.mime.text import MIMEText

import anthropic
from django.conf import settings
from googleapiclient.discovery import build

from apps.orchestrator.models import Client

from .models import EmailAccount, EmailDraft
from .oauth import get_credentials


def _gmail_service(account: EmailAccount):
    credentials = get_credentials(account)
    return build("gmail", "v1", credentials=credentials)


def _header(headers: list[dict], name: str) -> str:
    return next((h["value"] for h in headers if h["name"].lower() == name.lower()), "")


def _extract_body(payload: dict) -> str:
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text
    return ""


def _list_unread(account: EmailAccount, max_results: int = 10) -> list[dict]:
    service = _gmail_service(account)
    results = (
        service.users()
        .messages()
        .list(userId="me", q="is:unread", maxResults=max_results)
        .execute()
    )
    message_ids = [m["id"] for m in results.get("messages", [])]

    summaries = []
    for message_id in message_ids:
        message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="metadata", metadataHeaders=["From", "Subject"])
            .execute()
        )
        headers = message.get("payload", {}).get("headers", [])
        summaries.append(
            {
                "id": message_id,
                "thread_id": message["threadId"],
                "from": _header(headers, "From"),
                "subject": _header(headers, "Subject"),
            }
        )

    account.last_unread_ids = message_ids
    account.save(update_fields=["last_unread_ids"])
    return summaries


def _draft_reply(account: EmailAccount, message_index: int, instruction: str | None) -> str:
    if not account.last_unread_ids or not (1 <= message_index <= len(account.last_unread_ids)):
        return "Не нашёл письмо с таким номером. Сначала проверьте входящие."

    message_id = account.last_unread_ids[message_index - 1]
    service = _gmail_service(account)
    message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = message.get("payload", {}).get("headers", [])
    sender = _header(headers, "From")
    subject = _header(headers, "Subject")
    body = _extract_body(message.get("payload", {})) or "(без текста)"

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=(
            "Ты помогаешь составить вежливый деловой ответ на email от имени "
            "клиента. Отвечай только текстом письма, без пояснений."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Письмо от: {sender}\nТема: {subject}\nТекст письма:\n{body}\n\n"
                    f"Инструкция клиента для ответа: {instruction or 'ответь по существу вежливо и кратко'}"
                ),
            }
        ],
    )
    draft_body = next((b.text for b in response.content if b.type == "text"), "")

    client_obj, _ = Client.objects.get_or_create(telegram_user_id=account.client.telegram_user_id)
    EmailDraft.objects.filter(client=client_obj, sent=False).delete()
    EmailDraft.objects.create(
        client=client_obj,
        email_account=account,
        gmail_message_id=message_id,
        gmail_thread_id=message["threadId"],
        to_address=sender,
        subject=f"Re: {subject}" if not subject.lower().startswith("re:") else subject,
        body=draft_body,
    )

    return (
        f"Черновик ответа для {sender}:\n\n{draft_body}\n\n"
        "Отправить это письмо? Напишите «да, отправляй» для подтверждения "
        "или «отмена», чтобы не отправлять."
    )


def _confirm_send(account: EmailAccount, client: Client) -> str:
    draft = EmailDraft.objects.filter(client=client, email_account=account, sent=False).first()
    if draft is None:
        return "Нет черновика, ожидающего подтверждения."

    service = _gmail_service(account)
    mime_message = MIMEText(draft.body)
    mime_message["To"] = draft.to_address
    mime_message["Subject"] = draft.subject
    mime_message["In-Reply-To"] = draft.gmail_message_id
    raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

    service.users().messages().send(
        userId="me",
        body={"raw": raw, "threadId": draft.gmail_thread_id},
    ).execute()

    draft.sent = True
    draft.save(update_fields=["sent"])
    return f"Письмо отправлено на {draft.to_address}."


def _cancel_draft(client: Client) -> str:
    deleted, _ = EmailDraft.objects.filter(client=client, sent=False).delete()
    return "Черновик отменён." if deleted else "Нет черновика для отмены."


def handle_message(
    telegram_user_id: int,
    text: str,
    intent: str | None = None,
    message_index: int | None = None,
    instruction: str | None = None,
) -> str:
    client, _ = Client.objects.get_or_create(telegram_user_id=telegram_user_id)
    account = EmailAccount.objects.filter(client=client).first()
    if account is None:
        start_url = f"{settings.GOOGLE_OAUTH_REDIRECT_URI.rsplit('/', 2)[0]}/oauth/start/?telegram_user_id={telegram_user_id}"
        return f"Почта ещё не подключена. Перейдите по ссылке и разрешите доступ: {start_url}"

    if intent == "check_inbox":
        unread = _list_unread(account)
        if not unread:
            return "Непрочитанных писем нет."
        lines = [f"{i}. {u['from']} — {u['subject']}" for i, u in enumerate(unread, start=1)]
        return "Непрочитанные письма:\n" + "\n".join(lines)

    if intent == "draft_reply" and message_index:
        return _draft_reply(account, message_index, instruction)

    if intent == "confirm_send":
        return _confirm_send(account, client)

    if intent == "cancel":
        return _cancel_draft(client)

    return "Почта подключена. Что сделать: проверить входящие или ответить на письмо?"
