from rest_framework import serializers
from .models import TimeEntry, WorkSession, PunchCycle
from employees.serializers import EmployeeSerializer

class TimeEntrySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    
    class Meta:
        model = TimeEntry
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class PunchCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PunchCycle
        fields = '__all__'
        read_only_fields = ('id', 'duration_hours', 'created_at', 'updated_at')

class WorkSessionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    employee_data = EmployeeSerializer(source='employee', read_only=True)
    punch_cycles = PunchCycleSerializer(many=True, read_only=True)
    
    class Meta:
        model = WorkSession
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class TimeEntryCreateSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    type = serializers.ChoiceField(choices=TimeEntry.TYPE_CHOICES)
    timestamp = serializers.DateTimeField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_employee_id(self, value):
        from employees.models import Employee
        try:
            employee = Employee.objects.get(id=value, is_active=True)
            return value
        except Employee.DoesNotExist:
            raise serializers.ValidationError('Employee not found or inactive.')

class WorkStatusSerializer(serializers.Serializer):
    can_punch_in = serializers.BooleanField()
    can_punch_out = serializers.BooleanField()
    can_start_break = serializers.BooleanField()
    can_end_break = serializers.BooleanField()
    current_status = serializers.CharField()
    last_action = TimeEntrySerializer(required=False, allow_null=True)