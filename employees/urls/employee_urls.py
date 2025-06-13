from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views.employee_views import EmployeeViewSet, BusinessHoursViewSet

router = DefaultRouter()
router.register(r'business-hours', BusinessHoursViewSet, basename='business-hours')
router.register(r'', EmployeeViewSet, basename='employees')

urlpatterns = router.urls