from django.urls import path
from .views import (
    ReportsOverviewView, EmployeeReportsView, 
    DailyReportsView, CSVExportView
)

urlpatterns = [
    path('overview/', ReportsOverviewView.as_view(), name='reports-overview'),
    path('employees/', EmployeeReportsView.as_view(), name='employee-reports'),
    path('daily/', DailyReportsView.as_view(), name='daily-reports'),
    path('export/csv/', CSVExportView.as_view(), name='csv-export'),
]