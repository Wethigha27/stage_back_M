
import os
import django
import sys
from datetime import datetime
from calendar import monthrange
from django.db.models import Count

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MESRS.settings')
django.setup()

from myapp.models import User, Service, PersonnelPAT, Absence

print("--- DEBUG RAPPORT MENSUEL START ---")

try:
    # Simulate for chef_pat
    user = User.objects.get(role='chef_pat')
    print(f"User: {user.username}")
    
    service = Service.objects.get(chef_service=user, type_service='pat')
    print(f"Service: {service.nom}")
    
    qs = PersonnelPAT.objects.filter(personne__service=service).select_related('personne', 'personne__service')
    print(f"PAT Count: {qs.count()}")
    
    mois = datetime.now().strftime('%Y-%m')
    debut_mois = datetime.strptime(f"{mois}-01", "%Y-%m-%d").date()
    _, last = monthrange(debut_mois.year, debut_mois.month)
    fin_mois = debut_mois.replace(day=last)
    
    print(f"Periode: {debut_mois} to {fin_mois}")
    
    # Test absences query
    absences_mois = Absence.objects.filter(
        personne__service=service,
        date_debut__lte=fin_mois,
        date_fin__gte=debut_mois
    ).values('type_absence').annotate(count=Count('id'))
    print(f"Absences query result: {list(absences_mois)}")

    # Test agents_absents query
    agents_absents = qs.filter(
        personne__absences__date_debut__lte=fin_mois,
        personne__absences__date_fin__gte=debut_mois
    ).distinct().count()
    print(f"Agents absents: {agents_absents}")
    
    # Test top absences
    top_abs = []
    for agent in qs:
        print(f"Checking agent: {agent.personne.prenom} {agent.personne.nom}")
        n = Absence.objects.filter(
            personne=agent.personne,
            date_debut__lte=fin_mois,
            date_fin__gte=debut_mois
        ).count()
        if n > 0:
            top_abs.append({
                'nom': f"{agent.personne.prenom} {agent.personne.nom}",
                'poste': agent.poste,
                'nombre_absences': n
            })
    print(f"Top absences: {top_abs}")
    
    print("SUCCESS: Simulation completed without error.")

except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print("--- DEBUG RAPPORT MENSUEL END ---")
