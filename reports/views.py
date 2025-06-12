from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.http import HttpResponse
from django.db.models import Sum, Avg, Count, Q
from datetime import datetime, timedelta
import csv
import io

from timetracking.models import WorkSession, TimeEntry
from employees.models import Employee
from .serializers import (
    ReportStatsSerializer, EmployeeStatsSerializer, 
    DailyReportSerializer, CSVExportSerializer
)

class ReportsOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get overview statistics for reports"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        employee_id = request.query_params.get('employee_id')

        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filter work sessions
        sessions = WorkSession.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )

        if employee_id:
            sessions = sessions.filter(employee_id=employee_id)

        # Calculate statistics
        stats = {
            'total_sessions': sessions.count(),
            'total_working_hours': sessions.aggregate(
                total=Sum('working_hours')
            )['total'] or 0,
            'total_break_time': sessions.aggregate(
                total=Sum('break_duration')
            )['total'] or 0,
            'late_arrivals': sessions.filter(is_late_in=True).count(),
            'early_departures': sessions.filter(is_early_out=True).count(),
            'average_hours_per_day': sessions.aggregate(
                avg=Avg('working_hours')
            )['avg'] or 0,
            'total_punch_cycles': sum(
                session.punch_cycles.count() for session in sessions
            )
        }

        serializer = ReportStatsSerializer(stats)
        return Response(serializer.data)

class EmployeeReportsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get employee-specific statistics"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        employee_id = request.query_params.get('employee_id')

        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get employees with sessions in the date range
        employees_query = Employee.objects.filter(
            work_sessions__date__gte=start_date,
            work_sessions__date__lte=end_date
        ).distinct()

        if employee_id:
            employees_query = employees_query.filter(id=employee_id)

        employee_stats = []
        
        for employee in employees_query:
            sessions = WorkSession.objects.filter(
                employee=employee,
                date__gte=start_date,
                date__lte=end_date
            )

            total_hours = sessions.aggregate(total=Sum('working_hours'))['total'] or 0
            sessions_count = sessions.count()
            late_count = sessions.filter(is_late_in=True).count()
            early_count = sessions.filter(is_early_out=True).count()
            punch_cycles = sum(session.punch_cycles.count() for session in sessions)

            stats = {
                'employee_id': employee.id,
                'employee_name': employee.name,
                'department': employee.department,
                'sessions': sessions_count,
                'total_hours': total_hours,
                'average_hours': total_hours / sessions_count if sessions_count > 0 else 0,
                'late_count': late_count,
                'early_count': early_count,
                'punch_cycles': punch_cycles,
                'attendance_rate': (
                    ((sessions_count - late_count - early_count) / sessions_count) * 100
                    if sessions_count > 0 else 0
                )
            }
            employee_stats.append(stats)

        serializer = EmployeeStatsSerializer(employee_stats, many=True)
        return Response(serializer.data)

class DailyReportsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get daily breakdown of hours and activities"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        employee_id = request.query_params.get('employee_id')

        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get daily aggregated data
        sessions = WorkSession.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )

        if employee_id:
            sessions = sessions.filter(employee_id=employee_id)

        # Group by date
        daily_data = {}
        for session in sessions:
            date_str = session.date.isoformat()
            if date_str not in daily_data:
                daily_data[date_str] = {
                    'date': session.date,
                    'hours': 0,
                    'sessions': 0,
                    'cycles': 0
                }
            
            daily_data[date_str]['hours'] += float(session.working_hours)
            daily_data[date_str]['sessions'] += 1
            daily_data[date_str]['cycles'] += session.punch_cycles.count()

        # Convert to list and sort by date
        daily_list = list(daily_data.values())
        daily_list.sort(key=lambda x: x['date'])

        serializer = DailyReportSerializer(daily_list, many=True)
        return Response(serializer.data)

class CSVExportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Export time tracking data to CSV"""
        serializer = CSVExportSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']
        employee_id = serializer.validated_data.get('employee_id')
        include_punch_cycles = serializer.validated_data['include_punch_cycles']

        # Get work sessions
        sessions = WorkSession.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).select_related('employee').prefetch_related('punch_cycles')

        if employee_id:
            sessions = sessions.filter(employee_id=employee_id)

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="timesheet-{start_date}-to-{end_date}.csv"'

        writer = csv.writer(response)
        
        # Write headers
        headers = [
            'Employee Name', 'Employee ID', 'Date', 'First Punch In', 
            'Last Punch Out', 'Total Hours', 'Break Duration (min)', 
            'Working Hours', 'Late Arrivals', 'Early Departures', 'Status'
        ]
        
        if include_punch_cycles:
            headers.append('Punch Cycles')
        
        writer.writerow(headers)

        # Write data
        for session in sessions:
            punch_cycles_text = ''
            if include_punch_cycles:
                cycles = session.punch_cycles.all()
                cycle_texts = []
                for i, cycle in enumerate(cycles):
                    cycle_text = f"Cycle {i+1}: {cycle.punch_in.strftime('%H:%M')}"
                    if cycle.punch_out:
                        cycle_text += f" - {cycle.punch_out.strftime('%H:%M')}"
                    else:
                        cycle_text += " - In Progress"
                    
                    if cycle.is_late_in:
                        cycle_text += " (Late)"
                    if cycle.is_early_out:
                        cycle_text += " (Early)"
                    
                    cycle_texts.append(cycle_text)
                
                punch_cycles_text = '; '.join(cycle_texts)

            row = [
                session.employee.name,
                session.employee.employee_id,
                session.date.strftime('%Y-%m-%d'),
                session.punch_in.strftime('%H:%M:%S') if session.punch_in else '',
                session.punch_out.strftime('%H:%M:%S') if session.punch_out else '',
                f"{session.total_hours:.2f}",
                f"{session.break_duration:.0f}",
                f"{session.working_hours:.2f}",
                '1' if session.is_late_in else '0',
                '1' if session.is_early_out else '0',
                session.get_status_display()
            ]
            
            if include_punch_cycles:
                row.append(punch_cycles_text)
            
            writer.writerow(row)

        return response