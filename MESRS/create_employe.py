#!/usr/bin/env python
"""
Script pour créer un utilisateur employé avec un profil Personne
Usage: python create_employe.py
"""
import os
import sys
import django
from datetime import date, datetime

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MESRS.settings')
django.setup()

from myapp.models import User, Service, Personne, Structure

def create_employe():
    """Crée un utilisateur employé avec un profil Personne"""
    username = 'employe'
    email = 'employe@mesrs.mr'
    password = 'employe123'
    
    # Vérifier si l'utilisateur existe déjà
    if User.objects.filter(username=username).exists():
        user = User.objects.get(username=username)
        print(f"✅ L'utilisateur '{username}' existe déjà !")
        print(f"   Email: {user.email}")
        print(f"   Rôle: {user.role}")
        print(f"   Actif: {user.is_active}")
        
        # Mettre à jour le mot de passe
        user.set_password(password)
        user.save()
        print(f"\n✅ Mot de passe mis à jour à '{password}'")
        
        # Vérifier si une Personne est associée
        try:
            personne = Personne.objects.get(user=user)
            print(f"\n✅ Profil Personne associé:")
            print(f"   Nom: {personne.nom} {personne.prenom}")
            print(f"   Service: {personne.service.nom if personne.service else 'Non assigné'}")
        except Personne.DoesNotExist:
            print(f"\n⚠️  Aucun profil Personne associé. Création d'un profil...")
            create_personne_for_user(user)
        
        print(f"\n📝 Pour vous connecter:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        return user
    else:
        # Créer l'utilisateur employé
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='employe',
            is_staff=False,
            is_superuser=False,
            first_name='Employé',
            last_name='Test',
            is_active=True
        )
        print(f"✅ Utilisateur employé créé avec succès !")
        
        # Créer un profil Personne associé
        create_personne_for_user(user)
        
        print(f"\n📝 Identifiants de connexion:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"\n⚠️  IMPORTANT: Changez le mot de passe en production !")
        
        return user

def create_personne_for_user(user):
    """Crée un profil Personne pour un utilisateur"""
    # Récupérer un service existant (ou créer un service par défaut)
    service = Service.objects.first()
    if not service:
        print("⚠️  Aucun service trouvé. Création d'un service par défaut...")
        service = Service.objects.create(
            nom='Service Général',
            type_service='pat',
            description='Service par défaut'
        )
        print(f"✅ Service '{service.nom}' créé")
    
    # Vérifier si une Personne existe déjà pour cet utilisateur
    if Personne.objects.filter(user=user).exists():
        personne = Personne.objects.get(user=user)
        print(f"✅ Profil Personne existe déjà pour cet utilisateur")
        return personne
    
    # Créer une Personne avec des données par défaut
    try:
        personne = Personne.objects.create(
            user=user,
            nom='Test',
            prenom='Employé',
            date_naissance=date(1990, 1, 1),
            lieu_naissance='Nouakchott',
            nni='1234567890',
            nationalite='Mauritanienne',
            genre='MASCULIN',
            situation_familiale='Célibataire',
            adresse='Nouakchott, Mauritanie',
            nom_pere='Père Test',
            dernier_diplome='Baccalauréat',
            pays_obtention_diplome='Mauritanie',
            annee_obtention_diplome=2010,
            specialite_formation='Général',
            fonction='Employé',
            type_employe='pat',
            numero_employe=f'EMP{user.id:04d}',
            date_embauche=date.today(),
            service=service,
            statut_actif=True
        )
        print(f"✅ Profil Personne créé avec succès !")
        print(f"   Nom: {personne.nom} {personne.prenom}")
        print(f"   Service: {personne.service.nom}")
        print(f"   Fonction: {personne.fonction}")
        return personne
    except Exception as e:
        print(f"❌ Erreur lors de la création du profil Personne: {e}")
        # Si le NNI existe déjà, essayer avec un autre
        if 'nni' in str(e).lower() or 'unique' in str(e).lower():
            try:
                # Générer un NNI unique
                import random
                nni = f'{random.randint(1000000000, 9999999999)}'
                while Personne.objects.filter(nni=nni).exists():
                    nni = f'{random.randint(1000000000, 9999999999)}'
                
                personne = Personne.objects.create(
                    user=user,
                    nom='Test',
                    prenom='Employé',
                    date_naissance=date(1990, 1, 1),
                    lieu_naissance='Nouakchott',
                    nni=nni,
                    nationalite='Mauritanienne',
                    genre='MASCULIN',
                    situation_familiale='Célibataire',
                    adresse='Nouakchott, Mauritanie',
                    nom_pere='Père Test',
                    dernier_diplome='Baccalauréat',
                    pays_obtention_diplome='Mauritanie',
                    annee_obtention_diplome=2010,
                    specialite_formation='Général',
                    fonction='Employé',
                    type_employe='pat',
                    numero_employe=f'EMP{user.id:04d}',
                    date_embauche=date.today(),
                    service=service,
                    statut_actif=True
                )
                print(f"✅ Profil Personne créé avec succès (NNI généré: {nni}) !")
                return personne
            except Exception as e2:
                print(f"❌ Erreur lors de la création avec NNI généré: {e2}")
                return None
        return None

if __name__ == '__main__':
    create_employe()

