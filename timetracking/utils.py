from django.utils import timezone
import pytz
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from .models import TimeEntry, WorkSession, PunchCycle
from employees.models import Employee, BusinessHours

CENTRAL_TZ = pytz.timezone('America/Chicago')

def to_local_chicago(dt):
    """Convert UTC datetime to Chicago local time (TEST: returns hardcoded time)"""
    if dt.tzinfo is None:
        dt = timezone.make_aware(dt, timezone.utc)
    return dt.astimezone(CENTRAL_TZ)


class TimeCalculationService:
    """Service class for time tracking calculations"""

    def create_time_entry(self, employee_id, entry_type, timestamp=None, notes=''):
        """Create a new time entry and update work session"""
        if timestamp is None:
            timestamp = timezone.now()
        # Always use local Chicago time for calculations
        local_timestamp = to_local_chicago(timestamp)
        employee = Employee.objects.get(id=employee_id, is_active=True)
        business_hours = BusinessHours.get_current()

        # Calculate late/early flags
        is_late = self._is_late_entry(local_timestamp, business_hours, entry_type)
        is_early = self._is_early_entry(local_timestamp, business_hours, entry_type)
        # Create time entry
        time_entry = TimeEntry.objects.create(
            employee=employee,
            type=entry_type,
            timestamp=timestamp,
            is_late=is_late,
            is_early=is_early,
            notes=notes
        )

        # Update or create work session
        self._update_work_session(employee, local_timestamp.date())

        return time_entry

    def get_current_work_status(self, employee_id):
        """Get current work status for an employee"""
        employee = Employee.objects.get(id=employee_id, is_active=True)
        today = to_local_chicago(timezone.now()).date()
        start_local = CENTRAL_TZ.localize(datetime.combine(today, time.min))
        end_local = CENTRAL_TZ.localize(datetime.combine(today, time.max))

        start_utc = start_local.astimezone(pytz.UTC)
        end_utc = end_local.astimezone(pytz.UTC)

        # Get today's entries
        today_entries = TimeEntry.objects.filter(
            employee=employee,
            timestamp__range=(start_utc, end_utc)
        ).order_by('timestamp')
        
        if not today_entries.exists():
            return {
                'can_punch_in': True,
                'can_punch_out': False,
                'can_start_break': False,
                'can_end_break': False,
                'current_status': 'not_started',
                'last_action': None
            }
        
        # Analyze entries to determine current status
        punch_ins = today_entries.filter(type='punch_in').count()
        punch_outs = today_entries.filter(type='punch_out').count()
        break_starts = today_entries.filter(type='break_start').count()
        break_ends = today_entries.filter(type='break_end').count()
        
        last_entry = today_entries.last()
        
        # Determine current status
        is_punched_in = punch_ins > punch_outs
        is_on_break = break_starts > break_ends
        
        if not is_punched_in:
            current_status = 'finished' if punch_outs > 0 else 'not_started'
            return {
                'can_punch_in': True,
                'can_punch_out': False,
                'can_start_break': False,
                'can_end_break': False,
                'current_status': current_status,
                'last_action': last_entry
            }
        elif is_on_break:
            return {
                'can_punch_in': False,
                'can_punch_out': False,
                'can_start_break': False,
                'can_end_break': True,
                'current_status': 'on_break',
                'last_action': last_entry
            }
        else:
            return {
                'can_punch_in': False,
                'can_punch_out': True,
                'can_start_break': True,
                'can_end_break': False,
                'current_status': 'working',
                'last_action': last_entry
            }

    def generate_work_sessions(self, start_date, end_date):
        """Generate work sessions for a date range"""
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        sessions = []
        current_date = start_date
        while current_date <= end_date:
            employees_with_entries = Employee.objects.filter(
                time_entries__timestamp__date=current_date
            ).distinct()
            for employee in employees_with_entries:
                session = self._update_work_session(employee, current_date)
                if session:
                    sessions.append(session)
            current_date += timedelta(days=1)
        return sessions

    def _update_work_session(self, employee, work_date):
        """Update or create work session for an employee and date"""
        # Get all time entries for this employee and date
        start_local = CENTRAL_TZ.localize(datetime.combine(work_date, time.min))
        end_local = CENTRAL_TZ.localize(datetime.combine(work_date, time.max))

        start_utc = start_local.astimezone(pytz.UTC)
        end_utc = end_local.astimezone(pytz.UTC)

        entries = TimeEntry.objects.filter(
            employee=employee,
            timestamp__range=(start_utc, end_utc)
        ).order_by('timestamp')
        
        if not entries.exists():
            return None
        
        # Get or create work session
        work_session, created = WorkSession.objects.get_or_create(
            employee=employee,
            date=work_date,
            defaults={
                'status': 'complete'
            }
        )
        
        # Calculate session data
        punch_ins = entries.filter(type='punch_in').order_by('timestamp')
        punch_outs = entries.filter(type='punch_out').order_by('timestamp')
        break_starts = entries.filter(type='break_start').order_by('timestamp')
        break_ends = entries.filter(type='break_end').order_by('timestamp')
        
        if punch_ins.exists():
            work_session.punch_in = to_local_chicago(punch_ins.first().timestamp)
            work_session.is_late_in = punch_ins.first().is_late
        if punch_outs.exists():
            work_session.punch_out = to_local_chicago(punch_outs.last().timestamp)
            work_session.is_early_out = punch_outs.last().is_early
        
        if break_starts.exists():
            work_session.break_start = to_local_chicago(break_starts.first().timestamp)

        if break_ends.exists():
            work_session.break_end = to_local_chicago(break_ends.last().timestamp)
        
        # Calculate hours and status
        self._calculate_session_hours(work_session, entries)
        self._update_session_status(work_session, entries)
        self._create_punch_cycles(work_session, punch_ins, punch_outs)
        
        work_session.save()
        return work_session

    def _calculate_session_hours(self, work_session, entries):
        """Calculate working hours and break duration for a session"""
        punch_ins = entries.filter(type='punch_in').order_by('timestamp')
        punch_outs = entries.filter(type='punch_out').order_by('timestamp')
        break_starts = entries.filter(type='break_start').order_by('timestamp')
        break_ends = entries.filter(type='break_end').order_by('timestamp')
        
        total_working_hours = Decimal('0')
        total_break_minutes = Decimal('0')
        
        # Calculate working time from punch cycles
        for i, punch_in in enumerate(punch_ins):
            if i < len(punch_outs):
                punch_out = punch_outs[i]
                # Convert timestamps to local time
                punch_in_local = to_local_chicago(punch_in.timestamp)
                punch_out_local = to_local_chicago(punch_out.timestamp)
                cycle_duration = punch_out_local - punch_in_local
                cycle_hours = Decimal(str(cycle_duration.total_seconds() / 3600))

                # Calculate break time within this cycle
                cycle_break_minutes = Decimal('0')
                for j, break_start in enumerate(break_starts):
                    break_start_local = to_local_chicago(break_start.timestamp)
                    if (break_start_local >= punch_in_local and 
                        break_start_local <= punch_out_local):
                        if j < len(break_ends):
                            break_end = break_ends[j]
                            break_end_local = to_local_chicago(break_end.timestamp)
                            if break_end_local <= punch_out_local:
                                break_duration = break_end_local - break_start_local
                                cycle_break_minutes += Decimal(str(break_duration.total_seconds() / 60))

                total_break_minutes += cycle_break_minutes
                total_working_hours += max(Decimal('0'), cycle_hours - (cycle_break_minutes / 60))
        
        # Handle ongoing work (punched in but not out)
        if len(punch_ins) > len(punch_outs):
            last_punch_in = punch_ins.last()
            last_punch_in_local = to_local_chicago(last_punch_in.timestamp)
            current_time = to_local_chicago(timezone.now())
            if current_time.date() == work_session.date:
                ongoing_duration = current_time - last_punch_in_local
                ongoing_hours = Decimal(str(ongoing_duration.total_seconds() / 3600))
                # Check for ongoing break
                ongoing_break_minutes = Decimal('0')
                if (break_starts.exists() and 
                    len(break_starts) > len(break_ends) and
                    to_local_chicago(break_starts.last().timestamp) >= last_punch_in_local):
                    break_duration = current_time - to_local_chicago(break_starts.last().timestamp)
                    ongoing_break_minutes = Decimal(str(break_duration.total_seconds() / 60))
                total_break_minutes += ongoing_break_minutes
                total_working_hours += max(Decimal('0'), ongoing_hours - (ongoing_break_minutes / 60))
        
        # Calculate total hours (first punch in to last punch out or current time)
        if work_session.punch_in:
            if work_session.punch_out:
                total_duration = work_session.punch_out - work_session.punch_in
            elif len(punch_ins) > len(punch_outs):
                total_duration = to_local_chicago(timezone.now()) - work_session.punch_in
            else:
                total_duration = timedelta(0)
            work_session.total_hours = Decimal(str(total_duration.total_seconds() / 3600))
        else:
            work_session.total_hours = Decimal('0')
        work_session.working_hours = total_working_hours
        work_session.break_duration = total_break_minutes

    def _update_session_status(self, work_session, entries):
        """Update session status based on current state"""
        punch_ins = entries.filter(type='punch_in').count()
        punch_outs = entries.filter(type='punch_out').count()
        break_starts = entries.filter(type='break_start').count()
        break_ends = entries.filter(type='break_end').count()
        
        is_punched_in = punch_ins > punch_outs
        is_on_break = break_starts > break_ends
        
        if not is_punched_in:
            work_session.status = 'complete'
        elif is_on_break:
            work_session.status = 'on_break'
        else:
            work_session.status = 'in_progress'

    def _create_punch_cycles(self, work_session, punch_ins, punch_outs):
        """Create punch cycles for the work session"""
        # Clear existing cycles
        work_session.punch_cycles.all().delete()
        
        for i, punch_in in enumerate(punch_ins):
            punch_out = punch_outs[i] if i < len(punch_outs) else None
            
            cycle = PunchCycle.objects.create(
                work_session=work_session,
                punch_in=punch_in.timestamp,
                punch_out=punch_out.timestamp if punch_out else None,
                is_late_in=punch_in.is_late,
                is_early_out=punch_out.is_early if punch_out else False
            )

    def _is_late_entry(self, timestamp, business_hours, entry_type):
        """Check if entry is late"""
        if entry_type != 'punch_in' or not business_hours:
            return False
        
        entry_time = timestamp.time()
        # Convert business_hours.start_time from UTC to Chicago
        utc_dt = datetime.combine(timestamp.date(), business_hours.start_time).replace(tzinfo=pytz.utc)
        start_time_chicago = utc_dt.astimezone(CENTRAL_TZ).time()
        late_threshold = (
            datetime.combine(timestamp.date(), start_time_chicago) + 
            timedelta(minutes=business_hours.late_threshold)
        ).time()
        return entry_time > late_threshold

    def _is_early_entry(self, timestamp, business_hours, entry_type):
        """Check if entry is early"""
        if entry_type != 'punch_out' or not business_hours:
            return False
        
        entry_time = timestamp.time()
        # Convert business_hours.end_time from UTC to Chicago
        utc_dt = datetime.combine(timestamp.date(), business_hours.end_time).replace(tzinfo=pytz.utc)
        end_time_chicago = utc_dt.astimezone(CENTRAL_TZ).time()
        scheduled_end_dt = datetime.combine(timestamp.date(), end_time_chicago).time()
        return entry_time < scheduled_end_dt