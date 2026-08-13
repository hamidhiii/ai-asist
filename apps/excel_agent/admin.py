from django.contrib import admin

from .models import ExcelUpload


@admin.register(ExcelUpload)
class ExcelUploadAdmin(admin.ModelAdmin):
    list_display = ["original_name", "client", "uploaded_at"]
