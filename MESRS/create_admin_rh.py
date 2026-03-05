#!/usr/bin/env python
"""
Script pour créer un utilisateur admin_rh
Usage: python manage.py shell < create_admin_rh.py
Ou: python create_admin_rh.py (si exécuté depuis le répertoire MESRS)
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MESRS.settings')
django.setup()

from myapp.models import User

def create_admin_rh():
    """Crée un utilisateur admin_rh s'il n'existe pas"""
    username = 'admin_rh'
    email = 'admin_rh@mesrs.mr'
    password = 'admin123'
    
    # Vérifier si l'utilisateur existe déjà
    if User.objects.filter(username=username).exists():
        admin = User.objects.get(username=username)
        print(f"✅ L'utilisateur '{username}' existe déjà !")
        print(f"   Email: {admin.email}")
        print(f"   Rôle: {admin.role}")
        print(f"   Actif: {admin.is_active}")
        print(f"\n📝 Pour vous connecter:")
        print(f"   Username: {username}")
        print(f"   Password: (le mot de passe actuel)")
        print(f"\n💡 Pour changer le mot de passe, utilisez:")
        print(f"   python manage.py changepassword {username}")
        return admin
    else:
        # Créer l'utilisateur admin_rh
        admin = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='admin_rh',
            is_staff=True,
            is_superuser=True,
            first_name='Admin',
            last_name='RH'
        )
        print(f"✅ Utilisateur admin_rh créé avec succès !")
        print(f"\n📝 Identifiants de connexion:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"\n⚠️  IMPORTANT: Changez le mot de passe en production !")
        return admin

if __name__ == '__main__':
    create_admin_rh()

