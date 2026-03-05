#!/usr/bin/env python
"""
Script pour créer un utilisateur chef_contractuel
Usage: python create_chef_contractuel.py
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MESRS.settings')
django.setup()

from myapp.models import User, Service

def create_chef_contractuel():
    """Crée un utilisateur chef_contractuel s'il n'existe pas"""
    username = 'chef_contractuel'
    email = 'chef_contractuel@mesrs.mr'
    password = 'chef123'
    
    # Vérifier si l'utilisateur existe déjà
    if User.objects.filter(username=username).exists():
        chef = User.objects.get(username=username)
        print(f"✅ L'utilisateur '{username}' existe déjà !")
        print(f"   Email: {chef.email}")
        print(f"   Rôle: {chef.role}")
        print(f"   Actif: {chef.is_active}")
        
        # Mettre à jour le mot de passe
        chef.set_password(password)
        chef.save()
        print(f"\n✅ Mot de passe mis à jour à '{password}'")
        
        print(f"\n📝 Pour vous connecter:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        return chef
    else:
        # Créer l'utilisateur chef_contractuel
        chef = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='chef_contractuel',
            is_staff=False,
            is_superuser=False,
            first_name='Chef',
            last_name='Contractuel',
            is_active=True
        )
        print(f"✅ Utilisateur chef_contractuel créé avec succès !")
        print(f"\n📝 Identifiants de connexion:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"\n⚠️  IMPORTANT: Changez le mot de passe en production !")
        
        # Vérifier s'il existe un service contractuel et l'associer
        try:
            service_contractuel = Service.objects.filter(type_service='contractuel').first()
            if service_contractuel:
                service_contractuel.chef_service = chef
                service_contractuel.save()
                print(f"\n✅ Service '{service_contractuel.nom}' associé au chef contractuel")
            else:
                print(f"\n⚠️  Aucun service de type 'contractuel' trouvé.")
                print(f"   Créez un service contractuel et associez-le à cet utilisateur via l'interface Admin RH.")
        except Exception as e:
            print(f"\n⚠️  Erreur lors de l'association du service: {e}")
        
        return chef

if __name__ == '__main__':
    create_chef_contractuel()

