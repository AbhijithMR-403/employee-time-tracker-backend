from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import login, logout
from ..models import CustomUser
from ..serializers import LoginSerializer, CustomUserSerializer


class LogoutView(APIView):
    # permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Delete the user's token
            request.user.auth_token.delete()
        except:
            pass
        
        logout(request)
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CustomUser.objects.all()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(role__icontains=search)
            )
        return queryset.order_by('-created_at')

    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        return Response({
            'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
            'is_active': user.is_active
        })

    def destroy(self, request, *args, **kwargs):
        # Prevent deletion of the last admin user
        if CustomUser.objects.filter(is_active=True).count() <= 1:
            return Response(
                {'error': 'Cannot delete the last active admin user'},
                status=status.HTTP_400_BAD_REQUEST
            )
        super().destroy(request, *args, **kwargs)
        return Response({'message': 'User deleted successfully'}, status=status.HTTP_200_OK)