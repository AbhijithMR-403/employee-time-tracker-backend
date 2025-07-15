from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TimeEntryViewSet, WorkSessionViewSet, TimeTrackingAPIView, WorkSessionEditAPIView

router = DefaultRouter()
router.register(r'entries', TimeEntryViewSet, basename='time-entries')
router.register(r'sessions', WorkSessionViewSet, basename='work-sessions')

urlpatterns = [
    path('punch/', TimeTrackingAPIView.as_view(), name='punch-action'),
    path('status/<uuid:employee_id>/', TimeTrackingAPIView.as_view(), name='work-status'),
    path('sessions/<uuid:pk>/edit/', WorkSessionEditAPIView.as_view(), name='worksession-edit'),
] + router.urls