"""Google OAuth flow for the Email agent.

One-time consent per client; after that we refresh silently using the
stored refresh_token. No password ever touches the bot or the database.
"""
from django.conf import settings
from google_auth_oauthlib.flow import Flow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def _build_flow(state: str | None = None) -> Flow:
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state,
        redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI,
    )


def build_authorization_url(telegram_user_id: int) -> str:
    flow = _build_flow(state=str(telegram_user_id))
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true")
    return auth_url


def exchange_code(code: str, state: str) -> dict:
    flow = _build_flow(state=state)
    flow.fetch_token(code=code)
    credentials = flow.credentials
    return {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "expiry": credentials.expiry,
    }
