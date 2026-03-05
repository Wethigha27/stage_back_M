
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MESRS.settings')
django.setup()

from myapp.models import User, Service

print("--- SIDIALI CHECK ---")
u = User.objects.filter(username='sidiali').first() or User.objects.filter(first_name='Sidi').first() or User.objects.get(id=7)
if u:
    print(f"USER: ID={u.id}, Username={u.username}, Role={u.role}, FullName={u.first_name} {u.last_name}")
    s = Service.objects.filter(chef_service=u).first()
    print(f"SERVICE: {s.id if s else 'NONE'} - {s.nom if s else 'NONE'}")
else:
    print("USER NOT FOUND")
