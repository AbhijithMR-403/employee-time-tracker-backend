from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from django.utils import timezone
from datetime import datetime, date, time, timedelta
from .models import TimeEntry, WorkSession, PunchCycle
from .serializers import (
    TimeEntrySerializer, WorkSessionSerializer, TimeEntryCreateSerializer, 
    WorkStatusSerializer, PunchCycleSerializer, WorkSessionEditSerializer
)
from employees.models import Employee, BusinessHours
from .utils import TimeCalculationService
from django.db.models import Prefetch
from rest_framework.generics import get_object_or_404

class TimeEntryViewSet(viewsets.ModelViewSet):
    queryset = TimeEntry.objects.all()
    serializer_class = TimeEntrySerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = TimeEntry.objects.select_related('employee').all()
        
        # Filter by employee
        employee_id = self.request.query_params.get('employee_id', None)
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)
        
        # Filter by type
        entry_type = self.request.query_params.get('type', None)
        if entry_type:
            queryset = queryset.filter(type=entry_type)
        
        return queryset.order_by('-timestamp')

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent time entries (last 50)"""
        entries = self.get_queryset()[:50]
        serializer = self.get_serializer(entries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's time entries for all employees"""
        today = timezone.now().date()
        entries = self.get_queryset().filter(timestamp__date=today)
        serializer = self.get_serializer(entries, many=True)
        return Response(serializer.data)

class WorkSessionViewSet(viewsets.ModelViewSet):
    queryset = WorkSession.objects.all()
    serializer_class = WorkSessionSerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = WorkSession.objects.select_related('employee').prefetch_related(
            Prefetch(
                'punch_cycles',
                queryset=PunchCycle.objects.order_by('-created_at')  # or Sort latest date to old 
            )
        )

        # Filter by employee
        employee_id = self.request.query_params.get('employee_id', None)
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.order_by('-date')

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate work sessions for a date range"""
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = TimeCalculationService()
            sessions = service.generate_work_sessions(start_date, end_date)
            
            return Response({
                'message': f'Generated {len(sessions)} work sessions',
                'sessions_count': len(sessions)
            })
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class WorkSessionEditAPIView(APIView):
    """Separate API to edit punch_in, punch_out, and note for a WorkSession."""
    def put(self, request, pk):
        work_session = get_object_or_404(WorkSession, pk=pk)
        serializer = WorkSessionEditSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        punch_in = data['punch_in']
        punch_out = data['punch_out']
        note = data.get('note', '')

        # Validation: punch_in must not be after punch_out
        if punch_in and punch_out and punch_in > punch_out:
            return Response({'error': 'Punch in time cannot be after Punch out time.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validation: punch in/out duration must not exceed 24 hours
        if punch_in and punch_out:
            duration = punch_out - punch_in
            if duration.total_seconds() > 24 * 3600:
                return Response({'error': 'Punch in and Punch out time cannot exceed 24 hours.'}, status=status.HTTP_400_BAD_REQUEST)

        # Update fields
        work_session.punch_in = punch_in
        work_session.punch_out = punch_out
        work_session.note = note

        # Calculate is_late_in and is_early_out using business logic
        from employees.models import BusinessHours
        business_hours = BusinessHours.get_current()
        # is_late_in
        if business_hours:
            late_threshold = (datetime.combine(punch_in.date(), business_hours.start_time) + timedelta(minutes=business_hours.late_threshold)).time()
            work_session.is_late_in = punch_in.time() > late_threshold
            # is_early_out
            scheduled_end = business_hours.end_time
            work_session.is_early_out = punch_out.time() < scheduled_end
        else:
            work_session.is_late_in = False
            work_session.is_early_out = False

        # Update status
        if punch_out:
            work_session.status = 'complete'
        else:
            work_session.status = 'in_progress'

        # Directly calculate total_hours and working_hours
        from decimal import Decimal
        if punch_in and punch_out:
            duration = punch_out - punch_in
            hours = Decimal(duration.total_seconds()) / Decimal(3600)
            work_session.total_hours = round(hours, 2)
            work_session.working_hours = round(hours, 2)
        else:
            work_session.total_hours = Decimal('0.00')
            work_session.working_hours = Decimal('0.00')

        work_session.save()
        return Response(WorkSessionSerializer(work_session).data)

class TimeTrackingAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        """Handle punch actions (punch in/out, break start/end)"""
        serializer = TimeEntryCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                service = TimeCalculationService()
                time_entry = service.create_time_entry(
                    employee_id=serializer.validated_data['employee_id'],
                    entry_type=serializer.validated_data['type'],
                    timestamp=serializer.validated_data.get('timestamp'),
                    notes=serializer.validated_data.get('notes', '')
                )
                
                return Response({
                    'message': 'Time entry created successfully',
                    'data': TimeEntrySerializer(time_entry).data
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response(
                    {'error': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, employee_id=None):
        """Get current work status for an employee"""
        if not employee_id:
            return Response(
                {'error': 'employee_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = TimeCalculationService()
            work_status = service.get_current_work_status(employee_id)
            
            serializer = WorkStatusSerializer(work_status)
            return Response(serializer.data)
            
        except Employee.DoesNotExist:
            return Response(
                {'error': 'Employee not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )