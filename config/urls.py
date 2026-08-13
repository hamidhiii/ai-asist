from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("telegram/", include("apps.telegram_bot.urls")),
    path("email/", include("apps.email_agent.urls")),
    path("api/tasks-payments/", include("apps.tasks_payments.urls")),
    path("api/excel/", include("apps.excel_agent.urls")),
]
