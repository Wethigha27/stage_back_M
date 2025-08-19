# myapp/urls.py - VERSION CORRIGÉE
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import *
from .authentication import CustomTokenObtainPairView

# Router principal
router = DefaultRouter()

# ✅ ENREGISTREMENT CORRECT DE TOUS LES VIEWSETS
router.register(r'users', UserViewSet)
router.register(r'services', ServiceViewSet)
router.register(r'personnes', PersonneViewSet)
router.register(r'enseignants', EnseignantViewSet, basename='enseignant')  # ✅ AJOUTÉ
router.register(r'personnel-pat', PersonnelPATViewSet, basename='personnelpat')
router.register(r'contractuels', ContractuelViewSet, basename='contractuel')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'permissions', PermissionViewSet, basename='permissions')
router.register(r'structures', StructureViewSet)
router.register(r'recrutements', RecrutementViewSet)
router.register(r'candidats', CandidatViewSet)
router.register(r'absences', AbsenceViewSet)
router.register(r'paies', PaieViewSet)
router.register(r'detachements', DetachementViewSet)
router.register(r'documents', DocumentViewSet)

# Enums ViewSets
router.register(r'statut-offres', StatutOffreViewSet)
router.register(r'type-structures', TypeStructureViewSet)
router.register(r'type-contrats', TypeContratViewSet)
router.register(r'type-absences', TypeAbsenceViewSet)
router.register(r'statut-paiements', StatutPaiementViewSet)
router.register(r'statut-absences', StatutAbsenceViewSet)
router.register(r'type-documents', TypeDocumentViewSet)
router.register(r'statut-candidatures', StatutCandidatureViewSet)
router.register(r'planning', PlanningViewSet, basename='planning')
router.register(r'statistiques', StatistiquesViewSet, basename='statistiques')
urlpatterns = [
    # API endpoints du router
    path('api/', include(router.urls)),
    
    # Authentification JWT
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/', include('rest_framework.urls')),
    
    # ✅ ENDPOINTS DE DEBUG (à supprimer en production)
    path('api/debug/user-info/', UserViewSet.as_view({'get': 'debug_user_info'}), name='debug-user-info'),
    path('api/debug/permissions/', PermissionViewSet.as_view({'get': 'test_hierarchie'}), name='debug-permissions'),
]