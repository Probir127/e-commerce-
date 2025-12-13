import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.contrib.auth.models import User

try:
    u = User.objects.get(username='admin')
    u.set_password('admin123')
    u.save()
    print("Password for 'admin' has been reset to 'admin123'.")
except User.DoesNotExist:
    print("User 'admin' not found. Creating new superuser...")
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Superuser 'admin' created with password 'admin123'.")
