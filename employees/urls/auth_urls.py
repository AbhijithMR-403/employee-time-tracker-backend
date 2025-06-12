from django.urls import path
from ..views.auth_views import LoginView, LogoutView, AdminUserViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'admin-users', AdminUserViewSet, basename='admin-users')

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
] + router.urls