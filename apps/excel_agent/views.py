from rest_framework import viewsets

from .agent import analyze_upload
from .models import ExcelUpload
from .serializers import ExcelUploadSerializer


class ExcelUploadViewSet(viewsets.ModelViewSet):
    queryset = ExcelUpload.objects.all()
    serializer_class = ExcelUploadSerializer

    def perform_create(self, serializer):
        upload = serializer.save(original_name=self.request.data["file"].name)
        analyze_upload(upload)
