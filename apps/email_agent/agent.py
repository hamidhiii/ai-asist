from django.conf import settings

from apps.orchestrator.models import Client

from .models import EmailAccount


def handle_message(telegram_user_id: int, text: str) -> str:
    client, _ = Client.objects.get_or_create(telegram_user_id=telegram_user_id)
    if not EmailAccount.objects.filter(client=client).exists():
        start_url = f"{settings.GOOGLE_OAUTH_REDIRECT_URI.rsplit('/', 2)[0]}/oauth/start/?telegram_user_id={telegram_user_id}"
        return f"Почта ещё не подключена. Перейдите по ссылке и разрешите доступ: {start_url}"
    # TODO: parse `text` into a search/send action once an account is connected.
    return "Почта подключена. Что сделать: проверить входящие или отправить письмо?"
