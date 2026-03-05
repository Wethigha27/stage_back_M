
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MESRS.settings')
django.setup()

from myapp.models import User, Service

print("ID | Username | Role | Full Name")
for u in User.objects.all():
    print(f"{u.id} | {u.username} | {u.role} | {u.first_name} {u.last_name}")

print("\nID | Service Name | Chef Username")
for s in Service.objects.all():
    print(f"{s.id} | {s.nom} | {s.chef_service.username if s.chef_service else 'NONE'}")
