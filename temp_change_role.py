import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()
from accounts.models import User
u = User.objects.get(username='scuadrador')
u.role = 'ADMIN'
u.save()
print('Role updated to', u.role)
