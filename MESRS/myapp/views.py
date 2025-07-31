from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    Structure, Personne, Enseignant, PersonnelPAT, Contractuel,
    Recrutement, Candidat, Absence, Paie, Detachement, Document,
    StatutOffre, TypeStructure, TypeEmploye, TypeContrat, TypeAbsence,
    StatutPaiement, StatutAbsence, TypeDocument, StatutCandidature
)

from .serializers import (
    StructureSerializer, PersonneSerializer, EnseignantSerializer,
    PersonnelPATSerializer, ContractuelSerializer, RecrutementSerializer,
    CandidatSerializer, AbsenceSerializer, PaieSerializer,
    DetachementSerializer, DocumentSerializer, StatutOffreSerializer,
    TypeStructureSerializer, TypeEmployeSerializer, TypeContratSerializer,
    TypeAbsenceSerializer, StatutPaiementSerializer, StatutAbsenceSerializer,
    TypeDocumentSerializer, StatutCandidatureSerializer,
    PersonneDetailSerializer, StructureTreeSerializer
)


class StructureViewSet(viewsets.ModelViewSet):
    queryset = Structure.objects.all()
    serializer_class = StructureSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_structure', 'parent_structure']
    search_fields = ['nom', 'description']
    ordering_fields = ['nom', 'type_structure']
    
    @action(detail=False, methods=['get'])
    def arborescence(self, request):
        """Retourne l'arborescence complète des structures"""
        structures_racine = Structure.objects.filter(parent_structure__isnull=True)
        serializer = StructureTreeSerializer(structures_racine, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def employes(self, request, pk=None):
        """Retourne tous les employés d'une structure"""
        structure = self.get_object()
        # Ici, vous devrez ajuster selon votre logique métier
        # pour associer les personnes aux structures
        return Response({'message': 'Fonctionnalité à implémenter'})


class PersonneViewSet(viewsets.ModelViewSet):
    queryset = Personne.objects.all()
    serializer_class = PersonneSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['genre', 'nationalite', 'situation_familiale', 'fonction']
    search_fields = ['nom', 'prenom', 'nni', 'fonction']
    ordering_fields = ['nom', 'prenom', 'date_naissance']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PersonneDetailSerializer
        return PersonneSerializer
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        """Retourne les statistiques des employés"""
        total = Personne.objects.count()
        par_genre = Personne.objects.values('genre').annotate(count=Count('id'))
        par_nationalite = Personne.objects.values('nationalite').annotate(count=Count('id'))
        
        return Response({
            'total': total,
            'par_genre': list(par_genre),
            'par_nationalite': list(par_nationalite)
        })


class EnseignantViewSet(viewsets.ModelViewSet):
    queryset = Enseignant.objects.select_related('personne').all()
    serializer_class = EnseignantSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['corps', 'grade', 'echelon']
    search_fields = ['personne__nom', 'personne__prenom', 'corps', 'grade']
    ordering_fields = ['personne__nom', 'grade', 'indice']
    
    @action(detail=False, methods=['get'])
    def par_grade(self, request):
        """Statistiques des enseignants par grade"""
        stats = Enseignant.objects.values('grade').annotate(count=Count('id'))
        return Response(list(stats))


class PersonnelPATViewSet(viewsets.ModelViewSet):
    queryset = PersonnelPAT.objects.select_related('personne').all()
    serializer_class = PersonnelPATSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['grade']
    search_fields = ['personne__nom', 'personne__prenom', 'grade']
    ordering_fields = ['personne__nom', 'grade', 'indice']


class ContractuelViewSet(viewsets.ModelViewSet):
    queryset = Contractuel.objects.select_related('personne').all()
    serializer_class = ContractuelSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_contrat']
    search_fields = ['personne__nom', 'personne__prenom']
    ordering_fields = ['personne__nom', 'date_debut_contrat']
    
    @action(detail=False, methods=['get'])
    def expires_bientot(self, request):
        """Contrats qui expirent dans les 30 prochains jours"""
        date_limite = timezone.now().date() + timedelta(days=30)
        contrats = Contractuel.objects.filter(
            date_fin_contrat__lte=date_limite,
            date_fin_contrat__gte=timezone.now().date()
        )
        serializer = self.get_serializer(contrats, many=True)
        return Response(serializer.data)


class RecrutementViewSet(viewsets.ModelViewSet):
    queryset = Recrutement.objects.select_related('structure_recruteur').all()
    serializer_class = RecrutementSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_employe', 'statut_offre', 'structure_recruteur']
    search_fields = ['nom', 'prenom', 'description']
    ordering_fields = ['date_limite', 'date_entree']


class CandidatViewSet(viewsets.ModelViewSet):
    queryset = Candidat.objects.all()
    serializer_class = CandidatSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['statut_candidature']
    search_fields = ['nom', 'prenom', 'email']
    ordering_fields = ['date_candidature', 'nom']


class AbsenceViewSet(viewsets.ModelViewSet):
    queryset = Absence.objects.select_related('personne').all()
    serializer_class = AbsenceSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_absence', 'statut', 'personne']
    search_fields = ['personne__nom', 'personne__prenom']
    ordering_fields = ['date_debut', 'date_demande_absence']
    
    @action(detail=False, methods=['get'])
    def en_cours(self, request):
        """Absences en cours"""
        aujourd_hui = timezone.now().date()
        absences = Absence.objects.filter(
            date_debut__lte=aujourd_hui,
            date_fin__gte=aujourd_hui,
            statut='APPROUVÉ'
        )
        serializer = self.get_serializer(absences, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        """Statistiques des absences"""
        stats = Absence.objects.values('type_absence').annotate(count=Count('id'))
        return Response(list(stats))


class PaieViewSet(viewsets.ModelViewSet):
    queryset = Paie.objects.select_related('personne').all()
    serializer_class = PaieSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['statut_paiement', 'mois_annee', 'personne']
    search_fields = ['personne__nom', 'personne__prenom']
    ordering_fields = ['date_paiement', 'mois_annee']
    
    @action(detail=False, methods=['get'])
    def resume_mensuel(self, request):
        """Résumé des paies par mois"""
        mois = request.query_params.get('mois')
        if not mois:
            return Response({'error': 'Paramètre mois requis (format: YYYY-MM)'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        paies = Paie.objects.filter(mois_annee=mois)
        total_brut = paies.aggregate(Sum('salaire_brut'))['salaire_brut__sum'] or 0
        total_net = paies.aggregate(Sum('salaire_net'))['salaire_net__sum'] or 0
        total_deductions = paies.aggregate(Sum('deductions'))['deductions__sum'] or 0
        
        return Response({
            'mois': mois,
            'nombre_employes': paies.count(),
            'total_brut': total_brut,
            'total_net': total_net,
            'total_deductions': total_deductions
        })


class DetachementViewSet(viewsets.ModelViewSet):
    queryset = Detachement.objects.select_related('personne', 'structure_origine', 'structure_detachement').all()
    serializer_class = DetachementSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['structure_origine', 'structure_detachement', 'personne']
    search_fields = ['personne__nom', 'personne__prenom']
    ordering_fields = ['date_debut_detachement', 'date_fin_detachement']


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.select_related('proprietaire').all()
    serializer_class = DocumentSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_document', 'proprietaire']
    search_fields = ['nom', 'proprietaire__nom', 'proprietaire__prenom']
    ordering_fields = ['date_upload', 'nom']


# ViewSets pour les modèles d'énumération
class StatutOffreViewSet(viewsets.ModelViewSet):
    queryset = StatutOffre.objects.all()
    serializer_class = StatutOffreSerializer
    permission_classes = [AllowAny]


class TypeStructureViewSet(viewsets.ModelViewSet):
    queryset = TypeStructure.objects.all()
    serializer_class = TypeStructureSerializer
    permission_classes = [AllowAny]


class TypeEmployeViewSet(viewsets.ModelViewSet):
    queryset = TypeEmploye.objects.all()
    serializer_class = TypeEmployeSerializer
    permission_classes = [AllowAny]


class TypeContratViewSet(viewsets.ModelViewSet):
    queryset = TypeContrat.objects.all()
    serializer_class = TypeContratSerializer
    permission_classes = [AllowAny]


class TypeAbsenceViewSet(viewsets.ModelViewSet):
    queryset = TypeAbsence.objects.all()
    serializer_class = TypeAbsenceSerializer
    permission_classes = [AllowAny]


class StatutPaiementViewSet(viewsets.ModelViewSet):
    queryset = StatutPaiement.objects.all()
    serializer_class = StatutPaiementSerializer
    permission_classes = [AllowAny]


class StatutAbsenceViewSet(viewsets.ModelViewSet):
    queryset = StatutAbsence.objects.all()
    serializer_class = StatutAbsenceSerializer
    permission_classes = [AllowAny]


class TypeDocumentViewSet(viewsets.ModelViewSet):
    queryset = TypeDocument.objects.all()
    serializer_class = TypeDocumentSerializer
    permission_classes = [AllowAny]


class StatutCandidatureViewSet(viewsets.ModelViewSet):
    queryset = StatutCandidature.objects.all()
    serializer_class = StatutCandidatureSerializer
    permission_classes = [AllowAny]