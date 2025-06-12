from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from ..models import Employee, BusinessHours
from ..serializers import EmployeeSerializer, BusinessHoursSerializer

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Employee.objects.all()
        
        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(employee_id__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(department__icontains=search) |
                models.Q(position__icontains=search)
            )
        
        # Filter by department
        department = self.request.query_params.get('department', None)
        if department:
            queryset = queryset.filter(department=department)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('name')

    @action(detail=False, methods=['get'])
    def departments(self, request):
        """Get list of all departments"""
        departments = Employee.objects.values_list('department', flat=True).distinct()
        return Response(list(departments))

    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """Toggle employee active status"""
        employee = self.get_object()
        employee.is_active = not employee.is_active
        employee.save()
        return Response({
            'message': f'Employee {"activated" if employee.is_active else "deactivated"} successfully',
            'is_active': employee.is_active
        })

    @action(detail=False, methods=['get'])
    def by_email(self, request):
        """Get employee by email (for URL parameter access)"""
        email = request.query_params.get('email', None)
        if not email:
            return Response({'error': 'Email parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            employee = Employee.objects.get(email__iexact=email, is_active=True)
            serializer = self.get_serializer(employee)
            return Response(serializer.data)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

class BusinessHoursViewSet(viewsets.ModelViewSet):
    queryset = BusinessHours.objects.all()
    serializer_class = BusinessHoursSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current active business hours"""
        business_hours = BusinessHours.get_current()
        if business_hours:
            serializer = self.get_serializer(business_hours)
            return Response(serializer.data)
        else:
            # Return default business hours if none configured
            default_data = {
                'start_time': '09:00:00',
                'end_time': '17:00:00',
                'break_duration': 60,
                'late_threshold': 15
            }
            return Response(default_data)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate specific business hours configuration"""
        business_hours = self.get_object()
        
        # Deactivate all other configurations
        BusinessHours.objects.filter(is_active=True).update(is_active=False)
        
        # Activate this one
        business_hours.is_active = True
        business_hours.save()
        
        return Response({
            'message': 'Business hours activated successfully',
            'data': self.get_serializer(business_hours).data
        })