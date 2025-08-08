# myapp/permissions.py
from rest_framework import permissions
from rest_framework.permissions import BasePermission

class IsAuthenticatedWithHierarchy(BasePermission):
    """
    Permission de base qui vérifie l'authentification et la hiérarchie
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

class IsAdminRHOrReadOnly(BasePermission):
    """
    Seul l'Admin RH peut modifier, les autres peuvent lire
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.method in permissions.SAFE_METHODS:
            return True
            
        return hasattr(request.user, 'role') and request.user.role == 'admin_rh'

class IsAdminRHOrChefService(BasePermission):
    """
    Admin RH ou Chef de Service peuvent accéder
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        if not hasattr(request.user, 'role'):
            return False
            
        return request.user.role in ['admin_rh', 'chef_enseignant', 'chef_pat', 'chef_contractuel']

class CanManageService(BasePermission):
    """
    Vérifie si l'utilisateur peut gérer ce service spécifique
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
            
        if request.user.role == 'admin_rh':
            return True
            
        # Chef de service ne peut gérer que son service
        if request.user.role.startswith('chef_'):
            if hasattr(obj, 'service'):
                return obj.service.chef_service == request.user
            elif hasattr(obj, 'chef_service'):
                return obj.chef_service == request.user
                
        return False