
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MESRS.settings')
django.setup()

from myapp.models import User, Service, Personne

print("--- USER DEBUG ---")
users = User.objects.all()
for u in users:
    print(f"Username: {u.username}, Role: {u.role}, Full Name: {u.first_name} {u.last_name}")
    try:
        p = Personne.objects.get(user=u)
        print(f"  -> Profile: {p.prenom} {p.nom}, Service: {p.service.nom if p.service else 'NONE'}")
    except Personne.DoesNotExist:
        print(f"  -> Profile: MISSING")
    
    services_led = Service.objects.filter(chef_service=u)
    if services_led.exists():
        print(f"  -> Chef of: {[s.nom for s in services_led]}")
    else:
        print(f"  -> Chef of: NONE")

print("\n--- SERVICE DEBUG ---")
services = Service.objects.all()
for s in services:
    chef = s.chef_service
    print(f"Service: {s.nom}, Type: {s.type_service}, Chef: {chef.username if chef else 'NONE'}")
