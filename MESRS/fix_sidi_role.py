
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MESRS.settings')
django.setup()

from myapp.models import User, Service, Personne

print("--- RE-ASSIGNING SIDI ALI AS EMPLOYEE ---")
try:
    u = User.objects.get(id=7)
    old_role = u.role
    u.role = 'employe'
    u.save()
    print(f"User {u.username} (ID 7) role changed: {old_role} -> {u.role}")
    
    # Remove from chef_service
    services = Service.objects.filter(chef_service=u)
    for s in services:
        s.chef_service = None
        s.save()
        print(f"Removed as chef of: {s.nom}")
        
    # Check Personne profile
    try:
        p = Personne.objects.get(user=u)
        print(f"Found Personne profile: {p.prenom} {p.nom}, Type: {p.type_employe}")
        if p.type_employe != 'contractuel':
            p.type_employe = 'contractuel'
            p.save()
            print("Updated Personne type_employe to 'contractuel'")
    except Personne.DoesNotExist:
        print("WARNING: User 7 has NO Personne profile. Creating a basic one...")
        # Since we might not have all fields, let's just warn for now or create a dummy one if needed.
        # Actually, let's check if there is an ORPHAN Personne for "Sidi Ali"
        orphan = Personne.objects.filter(nom='Ali', prenom='Sidi').first()
        if orphan:
            orphan.user = u
            orphan.save()
            print(f"Linked orphan Personne ID {orphan.id} to User 7")
        else:
            print("No orphan Personne found for Sidi Ali.")

except User.DoesNotExist:
    print("User ID 7 not found!")
except Exception as e:
    print(f"ERROR: {str(e)}")
