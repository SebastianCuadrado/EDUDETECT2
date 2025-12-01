from accounts.models import User
u = User.objects.get(username='scuadrador')
u.role = 'ADMIN'
u.save()
print('Role updated to', u.role)
import sys
sys.exit()
