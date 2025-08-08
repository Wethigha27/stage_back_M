# ==== CORRECTION 1: authentication.py amélioré ====

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.core.exceptions import ObjectDoesNotExist

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    
    def validate(self, attrs):
        # Debug: Afficher les données reçues
        print(f"🔍 Tentative de connexion: {attrs.get('username')}")
        
        # Authentification normale
        try:
            data = super().validate(attrs)
        except Exception as e:
            print(f"❌ Erreur d'authentification: {e}")
            raise
        
        # Enrichir la réponse avec les infos utilisateur
        user_data = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': getattr(self.user, 'role', 'employe'),
            'service_id': None,
            'service_name': None,
            'permissions': self.get_user_permissions(),
            'full_name': self.user.get_full_name() or self.user.username
        }
        
        # Informations sur le service
        service_info = self.get_service_info()
        if service_info:
            user_data.update(service_info)
        
        data['user'] = user_data
        
        print(f"✅ Connexion réussie pour {self.user.username} (rôle: {user_data['role']})")
        return data
    
    def get_service_info(self):
        """Récupère les informations du service selon le rôle"""
        try:
            # Si l'utilisateur a un profil Personne avec un service
            if hasattr(self.user, 'personne') and self.user.personne and self.user.personne.service:
                service = self.user.personne.service
                return {
                    'service_id': service.id,
                    'service_name': service.nom,
                    'service_type': service.type_service,
                    'is_chef': False
                }
            
            # Si c'est un chef de service
            elif self.user.role and self.user.role.startswith('chef_'):
                from .models import Service
                try:
                    service = Service.objects.get(chef_service=self.user)
                    return {
                        'service_id': service.id,
                        'service_name': service.nom,
                        'service_type': service.type_service,
                        'is_chef': True
                    }
                except Service.DoesNotExist:
                    print(f"⚠️  Chef {self.user.username} n'a pas de service assigné")
                    return None
                    
        except Exception as e:
            print(f"⚠️  Erreur lors de la récupération du service: {e}")
            return None
        
        return None
    
    def get_user_permissions(self):
        """Retourne les permissions selon le rôle"""
        role = getattr(self.user, 'role', 'employe')
        
        permissions_map = {
            'admin_rh': [
                'view_all', 'add_all', 'change_all', 'delete_all', 
                'approve_all', 'manage_users', 'assign_roles',
                'view_dashboard_admin', 'manage_services'
            ],
            'chef_enseignant': [
                'view_service_enseignant', 'add_enseignant', 'change_enseignant',
                'approve_absence_enseignant', 'view_paie_service', 
                'view_dashboard_chef', 'manage_team_enseignant'
            ],
            'chef_pat': [
                'view_service_pat', 'add_pat', 'change_pat',
                'approve_absence_pat', 'view_paie_service',
                'view_dashboard_chef', 'manage_team_pat'
            ],
            'chef_contractuel': [
                'view_service_contractuel', 'add_contractuel', 'change_contractuel',
                'approve_absence_contractuel', 'view_paie_service',
                'view_dashboard_chef', 'manage_team_contractuel'
            ],
            'employe': [
                'view_self', 'change_self', 'request_absence', 
                'view_own_paie', 'view_own_documents', 'view_dashboard_personal'
            ]
        }
        
        return permissions_map.get(role, ['view_self'])

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        # Debug
        print(f"🔍 Requête de connexion reçue: {request.data}")
        
        try:
            response = super().post(request, *args, **kwargs)
            print(f"✅ Réponse d'authentification: Status {response.status_code}")
            return response
        except Exception as e:
            print(f"❌ Erreur lors de l'authentification: {e}")
            return Response({
                'error': 'Échec de l\'authentification',
                'detail': str(e)
            }, status=status.HTTP_401_UNAUTHORIZED)