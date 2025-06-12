# Time Tracker Backend

Django REST API backend for the Time Tracking System.

## Features

- **Employee Management**: CRUD operations for employees
- **Time Tracking**: Punch in/out, break tracking with business rules
- **Admin Authentication**: Secure admin user management
- **Reports & Analytics**: Comprehensive reporting with CSV export
- **Business Hours Configuration**: Configurable work hours and policies
- **AWS Ready**: Designed for deployment on AWS with RDS

## Quick Start

### Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

3. **Database Setup**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

### Docker Development

1. **Start Services**
   ```bash
   docker-compose up -d
   ```

2. **Run Migrations**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

3. **Create Superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

## API Endpoints

### Authentication
- `POST /api/auth/login/` - Admin login
- `POST /api/auth/logout/` - Admin logout
- `GET /api/auth/admin-users/` - List admin users
- `POST /api/auth/admin-users/` - Create admin user

### Employees
- `GET /api/employees/` - List employees
- `POST /api/employees/` - Create employee
- `GET /api/employees/{id}/` - Get employee details
- `PUT /api/employees/{id}/` - Update employee
- `GET /api/employees/by_email/?email=` - Get employee by email

### Business Hours
- `GET /api/employees/business-hours/current/` - Get current business hours
- `POST /api/employees/business-hours/` - Create business hours config

### Time Tracking
- `POST /api/timetracking/punch/` - Record punch action
- `GET /api/timetracking/status/{employee_id}/` - Get work status
- `GET /api/timetracking/entries/` - List time entries
- `GET /api/timetracking/sessions/` - List work sessions

### Reports
- `GET /api/reports/overview/` - Get overview statistics
- `GET /api/reports/employees/` - Get employee reports
- `GET /api/reports/daily/` - Get daily breakdown
- `POST /api/reports/export/csv/` - Export CSV report

## AWS Deployment

### Prerequisites
- AWS CLI configured
- Docker installed
- Python 3.11+

### Deploy to AWS

1. **Navigate to deployment directory**
   ```bash
   cd aws-deployment
   ```

2. **Run deployment script**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

The script will:
- Create AWS infrastructure (VPC, RDS, ECS, ALB)
- Build and push Docker image to ECR
- Deploy application to ECS Fargate
- Set up database and create admin user

### Manual AWS Setup

1. **Deploy Infrastructure**
   ```bash
   aws cloudformation deploy \
     --template-file cloudformation-template.yaml \
     --stack-name timetracker-infrastructure \
     --capabilities CAPABILITY_IAM
   ```

2. **Build and Push Image**
   ```bash
   # Get ECR login
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
   
   # Build and push
   docker build -t timetracker-backend .
   docker tag timetracker-backend:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/timetracker-backend:latest
   docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/timetracker-backend:latest
   ```

3. **Deploy ECS Service**
   ```bash
   aws ecs create-service --cli-input-json file://ecs-service.json
   ```

## Environment Variables

### Required
- `SECRET_KEY` - Django secret key
- `DB_NAME` - Database name
- `DB_USER` - Database username
- `DB_PASSWORD` - Database password
- `DB_HOST` - Database host

### Optional
- `DEBUG` - Debug mode (default: False)
- `ALLOWED_HOSTS` - Allowed hosts (comma-separated)
- `CORS_ALLOWED_ORIGINS` - CORS origins (comma-separated)
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_STORAGE_BUCKET_NAME` - S3 bucket for static files

## Database Schema

### Core Models
- **Employee** - Employee information and status
- **TimeEntry** - Individual punch/break actions
- **WorkSession** - Calculated daily work sessions
- **PunchCycle** - Individual punch in/out cycles
- **BusinessHours** - Configurable business rules
- **CustomUser** - Admin user management

### Key Features
- Automatic work session calculation
- Late/early detection based on business hours
- Multiple punch in/out cycles per day
- Break time tracking and calculation
- Comprehensive audit trail

## Development

### Project Structure
```
backend/
├── timetracker_project/     # Django project settings
├── employees/               # Employee and admin management
├── timetracking/           # Time tracking core functionality
├── reports/                # Reporting and analytics
├── aws-deployment/         # AWS deployment files
└── requirements.txt        # Python dependencies
```

### Key Services
- **TimeCalculationService** - Core time tracking logic
- **Employee Management** - CRUD operations for employees
- **Report Generation** - Analytics and CSV export
- **Admin Authentication** - Secure admin access

### Testing
```bash
python manage.py test
```

### Code Quality
```bash
# Linting
flake8 .

# Type checking
mypy .
```

## Production Considerations

### Security
- Use strong SECRET_KEY in production
- Enable SSL/HTTPS
- Configure proper CORS origins
- Use AWS Secrets Manager for sensitive data

### Performance
- Enable database connection pooling
- Use Redis for caching
- Configure CloudFront for static files
- Monitor with CloudWatch

### Scaling
- Use ECS auto-scaling
- Configure RDS read replicas
- Implement database indexing
- Use Celery for background tasks

## Support

For issues and questions:
1. Check the logs: `docker-compose logs web`
2. Review AWS CloudWatch logs
3. Verify environment variables
4. Check database connectivity

## License

This project is licensed under the MIT License.