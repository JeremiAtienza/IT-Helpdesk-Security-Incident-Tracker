"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Run migrations on startup (safe: idempotent, only creates missing tables)
try:
    call_command('migrate', '--noinput', verbosity=0)
except Exception as e:
    print(f"Migration error (non-blocking): {e}")
# Create default admin user if it doesn't exist
try:
    from django.contrib.auth.models import User
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("Created default admin user: admin / admin123")
except Exception as e:
    print(f"User creation error (non-blocking): {e}")
