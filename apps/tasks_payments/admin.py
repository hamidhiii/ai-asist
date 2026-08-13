from django.contrib import admin

from .models import Payment, Reminder, Task


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["counterparty", "amount", "currency", "due_date", "status", "client"]
    list_filter = ["status", "currency"]
    search_fields = ["counterparty", "note"]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "due_date", "status", "client"]
    list_filter = ["status"]


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ["client", "remind_at", "sent", "payment", "task"]
    list_filter = ["sent"]
