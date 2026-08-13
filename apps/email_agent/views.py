from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_GET
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from apps.orchestrator.models import Client

from .models import EmailAccount
from .oauth import build_authorization_url, exchange_code


@require_GET
def oauth_start(request: HttpRequest) -> HttpResponse:
    telegram_user_id = request.GET["telegram_user_id"]
    return HttpResponseRedirect(build_authorization_url(int(telegram_user_id)))


@require_GET
def oauth_callback(request: HttpRequest) -> HttpResponse:
    code = request.GET["code"]
    state = request.GET["state"]
    tokens = exchange_code(code, state)

    credentials = Credentials(token=tokens["access_token"], refresh_token=tokens["refresh_token"])
    profile = build("gmail", "v1", credentials=credentials).users().getProfile(userId="me").execute()

    client, _ = Client.objects.get_or_create(telegram_user_id=int(state))
    EmailAccount.objects.update_or_create(
        client=client,
        email_address=profile["emailAddress"],
        defaults={
            "provider": EmailAccount.Provider.GMAIL,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_expiry": tokens["expiry"],
        },
    )
    return HttpResponse("Почта подключена. Можете вернуться в Telegram.")
