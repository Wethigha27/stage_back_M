from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

from .views import (
    StructureViewSet, PersonneViewSet, EnseignantViewSet,
    PersonnelPATViewSet, ContractuelViewSet, RecrutementViewSet,
    CandidatViewSet, AbsenceViewSet, PaieViewSet, DetachementViewSet,
    DocumentViewSet, StatutOffreViewSet, TypeStructureViewSet,
    TypeEmployeViewSet, TypeContratViewSet, TypeAbsenceViewSet,
    StatutPaiementViewSet, StatutAbsenceViewSet, TypeDocumentViewSet,
    StatutCandidatureViewSet
)

# Création du routeur pour les ViewSets
router = DefaultRouter()

# Enregistrement des ViewSets principaux
router.register(r'structures', StructureViewSet)
router.register(r'personnes', PersonneViewSet)
router.register(r'enseignants', EnseignantViewSet)
router.register(r'personnel-pat', PersonnelPATViewSet)
router.register(r'contractuels', ContractuelViewSet)
router.register(r'recrutements', RecrutementViewSet)
router.register(r'candidats', CandidatViewSet)
router.register(r'absences', AbsenceViewSet)
router.register(r'paies', PaieViewSet)
router.register(r'detachements', DetachementViewSet)
router.register(r'documents', DocumentViewSet)

# Enregistrement des ViewSets d'énumération
router.register(r'statut-offres', StatutOffreViewSet)
router.register(r'type-structures', TypeStructureViewSet)
router.register(r'type-employes', TypeEmployeViewSet)
router.register(r'type-contrats', TypeContratViewSet)
router.register(r'type-absences', TypeAbsenceViewSet)
router.register(r'statut-paiements', StatutPaiementViewSet)
router.register(r'statut-absences', StatutAbsenceViewSet)
router.register(r'type-documents', TypeDocumentViewSet)
router.register(r'statut-candidatures', StatutCandidatureViewSet)

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Authentification
    path('api/auth/token/', obtain_auth_token, name='api_token_auth'),
    path('api/auth/', include('rest_framework.urls')),
]