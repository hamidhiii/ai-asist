from django.urls import path

from . import views

urlpatterns = [
    path("oauth/start/", views.oauth_start, name="email-oauth-start"),
    path("oauth/callback/", views.oauth_callback, name="email-oauth-callback"),
]
