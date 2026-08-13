from rest_framework.routers import DefaultRouter

from .views import ExcelUploadViewSet

router = DefaultRouter()
router.register("uploads", ExcelUploadViewSet, basename="excel-upload")

urlpatterns = router.urls
