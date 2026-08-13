from django.db import models

from apps.orchestrator.models import Client


class ExcelUpload(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="excel_uploads", null=True, blank=True)
    file = models.FileField(upload_to="excel_uploads/%Y/%m/")
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return self.original_name
