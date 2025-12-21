#!/bin/bash
set -e

echo "Starting Django Backend..."

# Wait for MySQL to be ready
echo "Waiting for MySQL (Django database)..."
while ! nc -z django_db 3306; do
  sleep 1
done
echo "MySQL (Django database) is ready!"

# Wait for DOMjudge database
echo "Waiting for DOMjudge database..."
while ! nc -z db 3306; do
  sleep 1
done
echo "DOMjudge database is ready!"

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if not exists (optional)
echo "Checking for superuser..."
python manage.py shell << 'END'
from users.models import User
import os

username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

if not User.objects.filter(username=username).exists():
    user = User.objects.create(
        username=username,
        email=email
    )
    user.set_password(password)
    user.save()
    print(f"Superuser '{username}' created successfully!")
else:
    print(f"Superuser '{username}' already exists.")
END

echo "Starting Gunicorn..."
# Start Gunicorn
exec gunicorn backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --threads 2 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --access-logfile - \
    --error-logfile - \
    --log-level info
