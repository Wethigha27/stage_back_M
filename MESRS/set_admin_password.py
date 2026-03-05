#!/usr/bin/env python
"""
Script pour définir le mot de passe admin_rh à 'admin123'
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MESRS.settings')
django.setup()

from myapp.models import User

def set_admin_password():
    """Définit le mot de passe de admin_rh à admin123"""
    username = 'admin_rh'
    password = 'admin123'
    
    try:
        admin = User.objects.get(username=username)
        admin.set_password(password)
        admin.save()
        print(f"✅ Mot de passe mis à jour avec succès pour '{username}' !")
        print(f"\n📝 Identifiants de connexion:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        return admin
    except User.DoesNotExist:
        # Créer l'utilisateur s'il n'existe pas
        admin = User.objects.create_user(
            username=username,
            email='admin_rh@mesrs.mr',
            password=password,
            role='admin_rh',
            is_staff=True,
            is_superuser=True,
            first_name='Admin',
            last_name='RH'
        )
        print(f"✅ Utilisateur '{username}' créé avec succès !")
        print(f"\n📝 Identifiants de connexion:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        return admin

if __name__ == '__main__':
    set_admin_password()

