from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TimeEntryViewSet, WorkSessionViewSet, TimeTrackingAPIView

router = DefaultRouter()
router.register(r'entries', TimeEntryViewSet, basename='time-entries')
router.register(r'sessions', WorkSessionViewSet, basename='work-sessions')

urlpatterns = [
    path('punch/', TimeTrackingAPIView.as_view(), name='punch-action'),
    path('status/<uuid:employee_id>/', TimeTrackingAPIView.as_view(), name='work-status'),
] + router.urls