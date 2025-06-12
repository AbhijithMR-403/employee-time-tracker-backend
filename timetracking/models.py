from django.db import models
from employees.models import Employee
import uuid

class TimeEntry(models.Model):
    """Time entry model for punch in/out and break tracking"""
    
    TYPE_CHOICES = [
        ('punch_in', 'Punch In'),
        ('punch_out', 'Punch Out'),
        ('break_start', 'Break Start'),
        ('break_end', 'Break End'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='time_entries')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    timestamp = models.DateTimeField()
    is_late = models.BooleanField(default=False)
    is_early = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['employee', 'timestamp']),
            models.Index(fields=['type', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.get_type_display()} at {self.timestamp}"

class WorkSession(models.Model):
    """Calculated work session for a specific employee and date"""
    
    STATUS_CHOICES = [
        ('complete', 'Complete'),
        ('in_progress', 'In Progress'),
        ('on_break', 'On Break'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='work_sessions')
    date = models.DateField()
    punch_in = models.DateTimeField(null=True, blank=True)
    punch_out = models.DateTimeField(null=True, blank=True)
    break_start = models.DateTimeField(null=True, blank=True)
    break_end = models.DateTimeField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    break_duration = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # in minutes
    working_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_late_in = models.BooleanField(default=False)
    is_early_out = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='complete')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['employee', 'date']
        ordering = ['-date', 'employee__name']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.date} ({self.working_hours}h)"

class PunchCycle(models.Model):
    """Individual punch in/out cycles within a work session"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_session = models.ForeignKey(WorkSession, on_delete=models.CASCADE, related_name='punch_cycles')
    punch_in = models.DateTimeField()
    punch_out = models.DateTimeField(null=True, blank=True)
    is_late_in = models.BooleanField(default=False)
    is_early_out = models.BooleanField(default=False)
    duration_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['punch_in']
        indexes = [
            models.Index(fields=['work_session', 'punch_in']),
        ]

    def __str__(self):
        return f"{self.work_session.employee.name} - Cycle {self.punch_in.strftime('%H:%M')}"

    def save(self, *args, **kwargs):
        # Calculate duration if punch_out exists
        if self.punch_out and self.punch_in:
            duration = self.punch_out - self.punch_in
            self.duration_hours = duration.total_seconds() / 3600
        super().save(*args, **kwargs)