
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MESRS.settings')
django.setup()

from myapp.models import User, Personne, Service

print("--- USERS AND PROFILES ---")
for u in User.objects.all():
    profile_info = "NO PROFILE"
    try:
        p = Personne.objects.get(user=u)
        profile_info = f"Profile: {p.prenom} {p.nom}, Type: {p.type_employe}, ID: {p.id}"
    except Personne.DoesNotExist:
        pass
    
    chef_of = [s.nom for s in Service.objects.filter(chef_service=u)]
    print(f"ID: {u.id} | User: {u.username} | Role: {u.role} | {profile_info} | Chef of: {chef_of}")
