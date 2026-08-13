from rest_framework import serializers

from .models import ExcelUpload


class ExcelUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcelUpload
        fields = ["id", "file", "original_name", "uploaded_at", "summary"]
        read_only_fields = ["id", "uploaded_at", "summary"]
