from django.contrib import admin

from .models import EmailAccount


@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    list_display = ["email_address", "provider", "client", "connected_at"]
    exclude = ["access_token", "refresh_token"]
