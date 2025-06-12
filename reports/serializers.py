from rest_framework import serializers
from timetracking.models import WorkSession
from employees.models import Employee

class ReportStatsSerializer(serializers.Serializer):
    total_sessions = serializers.IntegerField()
    total_working_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_break_time = serializers.DecimalField(max_digits=10, decimal_places=2)
    late_arrivals = serializers.IntegerField()
    early_departures = serializers.IntegerField()
    average_hours_per_day = serializers.DecimalField(max_digits=5, decimal_places=2)
    total_punch_cycles = serializers.IntegerField()

class EmployeeStatsSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    employee_name = serializers.CharField()
    department = serializers.CharField()
    sessions = serializers.IntegerField()
    total_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_hours = serializers.DecimalField(max_digits=5, decimal_places=2)
    late_count = serializers.IntegerField()
    early_count = serializers.IntegerField()
    punch_cycles = serializers.IntegerField()
    attendance_rate = serializers.DecimalField(max_digits=5, decimal_places=2)

class DailyReportSerializer(serializers.Serializer):
    date = serializers.DateField()
    hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    sessions = serializers.IntegerField()
    cycles = serializers.IntegerField()

class CSVExportSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    employee_id = serializers.UUIDField(required=False)
    include_punch_cycles = serializers.BooleanField(default=True)