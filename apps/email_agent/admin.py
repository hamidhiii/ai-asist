from django.contrib import admin

from .models import EmailAccount, EmailDraft


@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    list_display = ["email_address", "provider", "client", "connected_at"]
    exclude = ["access_token", "refresh_token"]


@admin.register(EmailDraft)
class EmailDraftAdmin(admin.ModelAdmin):
    list_display = ["to_address", "subject", "client", "sent", "created_at"]
    exclude = ["body"]
