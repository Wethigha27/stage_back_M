# myapp/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import *
from .authentication import CustomTokenObtainPairView

router = DefaultRouter()

# ========================================
# ENDPOINTS HIÉRARCHIQUES PRINCIPAUX
# ========================================

# Nouveaux endpoints hiérarchiques
router.register(r'users', UserViewSet)
router.register(r'services', ServiceViewSet)
router.register(r'personnes', PersonneViewSet)
router.register(r'enseignants', EnseignantViewSet, basename='enseignant')
router.register(r'personnel-pat', PersonnelPATViewSet, basename='personnel-pat')
router.register(r'contractuels', ContractuelViewSet, basename='contractuel')

# Dashboard et permissions
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'permissions', PermissionViewSet, basename='permissions')

# ========================================
# ENDPOINTS EXISTANTS ADAPTÉS
# ========================================

router.register(r'structures', StructureViewSet)
router.register(r'recrutements', RecrutementViewSet)
router.register(r'candidats', CandidatViewSet)
router.register(r'absences', AbsenceViewSet)
router.register(r'paies', PaieViewSet)
router.register(r'detachements', DetachementViewSet)
router.register(r'documents', DocumentViewSet)

# ========================================
# ENDPOINTS D'ÉNUMÉRATION
# ========================================

router.register(r'statut-offres', StatutOffreViewSet)
router.register(r'type-structures', TypeStructureViewSet)
router.register(r'type-contrats', TypeContratViewSet)
router.register(r'type-absences', TypeAbsenceViewSet)
router.register(r'statut-paiements', StatutPaiementViewSet)
router.register(r'statut-absences', StatutAbsenceViewSet)
router.register(r'type-documents', TypeDocumentViewSet)
router.register(r'statut-candidatures', StatutCandidatureViewSet)

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Authentification JWT
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Authentification classique (gardez pour compatibilité)
    path('api/auth/', include('rest_framework.urls')),
]