from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import EmailValidator
import uuid

class CustomUser(AbstractUser):
    """Extended user model for admin users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    role = models.CharField(max_length=50, default='Admin')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

class Employee(models.Model):
    """Employee model for time tracking"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    department = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['email']),
            models.Index(fields=['department']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.employee_id})"

class BusinessHours(models.Model):
    """Business hours configuration"""
    start_time = models.TimeField(help_text="Business start time")
    end_time = models.TimeField(help_text="Business end time")
    break_duration = models.PositiveIntegerField(
        default=60, 
        help_text="Standard break duration in minutes"
    )
    late_threshold = models.PositiveIntegerField(
        default=15, 
        help_text="Late arrival threshold in minutes"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Business Hours"
        ordering = ['-created_at']

    def __str__(self):
        return f"Business Hours: {self.start_time} - {self.end_time}"

    def save(self, *args, **kwargs):
        # Ensure only one active business hours configuration
        if self.is_active:
            BusinessHours.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_current(cls):
        """Get the current active business hours configuration"""
        return cls.objects.filter(is_active=True).first()