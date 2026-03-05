#!/usr/bin/env python
"""
Script pour supprimer le profil Personne d'un employé (pour tester l'onboarding)
Usage: python delete_employe_profil.py
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MESRS.settings')
django.setup()

from myapp.models import User, Personne

def delete_employe_profil():
    """Supprime le profil Personne de l'utilisateur employé"""
    username = 'employe'
    
    try:
        user = User.objects.get(username=username)
        print(f"✅ Utilisateur '{username}' trouvé")
        
        # Vérifier si une Personne est associée
        try:
            personne = Personne.objects.get(user=user)
            print(f"📋 Profil Personne trouvé:")
            print(f"   Nom: {personne.nom} {personne.prenom}")
            print(f"   Service: {personne.service.nom if personne.service else 'Non assigné'}")
            
            # Supprimer le profil
            personne.delete()
            print(f"\n✅ Profil Personne supprimé avec succès !")
            print(f"\n📝 À la prochaine connexion avec '{username}',")
            print(f"   le formulaire d'onboarding sera affiché automatiquement.")
            
        except Personne.DoesNotExist:
            print(f"ℹ️  Aucun profil Personne associé à cet utilisateur.")
            print(f"   L'onboarding sera déjà déclenché à la prochaine connexion.")
        
    except User.DoesNotExist:
        print(f"❌ L'utilisateur '{username}' n'existe pas.")
        print(f"   Créez-le d'abord avec: python create_employe.py")

if __name__ == '__main__':
    delete_employe_profil()

