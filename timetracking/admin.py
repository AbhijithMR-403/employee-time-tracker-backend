from django.contrib import admin
from .models import TimeEntry, WorkSession, PunchCycle

@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'type', 'timestamp', 'is_late', 'is_early', 'created_at')
    list_filter = ('type', 'is_late', 'is_early', 'timestamp', 'created_at')
    search_fields = ('employee__name', 'employee__employee_id', 'notes')
    ordering = ('-timestamp',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'timestamp'

@admin.register(WorkSession)
class WorkSessionAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'working_hours', 'break_duration', 'status', 'is_late_in', 'is_early_out')
    list_filter = ('status', 'is_late_in', 'is_early_out', 'date')
    search_fields = ('employee__name', 'employee__employee_id')
    ordering = ('-date', 'employee__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'date'

@admin.register(PunchCycle)
class PunchCycleAdmin(admin.ModelAdmin):
    list_display = ('work_session', 'punch_in', 'punch_out', 'duration_hours', 'is_late_in', 'is_early_out')
    list_filter = ('is_late_in', 'is_early_out', 'punch_in')
    search_fields = ('work_session__employee__name',)
    ordering = ('-punch_in',)
    readonly_fields = ('id', 'duration_hours', 'created_at', 'updated_at')