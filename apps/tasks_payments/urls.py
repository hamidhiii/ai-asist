from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, TaskViewSet

router = DefaultRouter()
router.register("payments", PaymentViewSet, basename="payment")
router.register("tasks", TaskViewSet, basename="task")

urlpatterns = router.urls
