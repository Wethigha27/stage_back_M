from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta

from .models import (
    User, Service, Structure, Personne, Enseignant, PersonnelPAT, Contractuel,
    Recrutement, Candidat, Absence, Paie, Detachement, Document,
    StatutOffre, TypeStructure, TypeContrat, TypeAbsence, 
    StatutPaiement, StatutAbsence, TypeDocument, StatutCandidature
)

from .serializers import (
    UserSerializer, ServiceSerializer, StructureSerializer, PersonneSerializer, 
    EnseignantSerializer, PersonnelPATSerializer, ContractuelSerializer, 
    RecrutementSerializer, CandidatSerializer, AbsenceSerializer, PaieSerializer,
    DetachementSerializer, DocumentSerializer, StatutOffreSerializer,
    TypeStructureSerializer, TypeContratSerializer,  
    TypeAbsenceSerializer, StatutPaiementSerializer, StatutAbsenceSerializer,
    TypeDocumentSerializer, StatutCandidatureSerializer,
    PersonneDetailSerializer, StructureTreeSerializer
)

from .permissions import IsAdminRHOrReadOnly, IsAdminRHOrChefService, CanManageService


# ========================================
# NOUVEAUX VIEWSETS HIÉRARCHIQUES - CHIVA
# ========================================

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les utilisateurs avec hiérarchie
    Seul Admin RH peut créer/modifier les utilisateurs
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminRHOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return User.objects.none()
            
        if user.role == 'admin_rh':
            return User.objects.all()
        elif user.role.startswith('chef_'):
            # Chef voit les employés de son service + lui-même
            try:
                service = Service.objects.get(chef_service=user)
                employes_ids = service.employes.filter(user__isnull=False).values_list('user_id', flat=True)
                return User.objects.filter(Q(id=user.id) | Q(id__in=employes_ids))
            except Service.DoesNotExist:
                return User.objects.filter(id=user.id)
        else:
            # Employé ne voit que lui-même
            return User.objects.filter(id=user.id)
    
    @action(detail=False, methods=['post'])
    def create_chef_service(self, request):
        """Créer un chef de service (Admin RH seulement)"""
        if request.user.role != 'admin_rh':
            return Response({'error': 'Permission refusée'}, status=403)
        
        data = request.data.copy()
        role = data.get('role')
        
        if not role or not role.startswith('chef_'):
            return Response({'error': 'Rôle chef requis'}, status=400)
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

class ServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les services avec hiérarchie
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['type_service']
    search_fields = ['nom', 'description']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Service.objects.none()
            
        if user.role == 'admin_rh':
            return Service.objects.all()
        elif user.role.startswith('chef_'):
            # Chef ne voit que son service
            return Service.objects.filter(chef_service=user)
        else:
            # Employé voit son service
            if hasattr(user, 'personne') and user.personne.service:
                return Service.objects.filter(id=user.personne.service.id)
        
        return Service.objects.none()
    
    @action(detail=True, methods=['get'])
    def employes(self, request, pk=None):
        """Retourne les employés d'un service"""
        service = self.get_object()
        employes = Personne.objects.filter(service=service)
        
        # Vérification des permissions
        if request.user.role != 'admin_rh':
            if service.chef_service != request.user:
                return Response({'error': 'Permission refusée'}, status=403)
        
        serializer = PersonneSerializer(employes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        """Statistiques des services"""
        queryset = self.get_queryset()
        stats = []
        
        for service in queryset:
            stats.append({
                'id': service.id,
                'nom': service.nom,
                'type_service': service.type_service,
                'chef_service': service.chef_service.get_full_name() if service.chef_service else None,
                'nombre_employes': service.employes.count(),
                'nombre_enseignants': service.employes.filter(type_employe='enseignant').count(),
                'nombre_pat': service.employes.filter(type_employe='pat').count(),
                'nombre_contractuels': service.employes.filter(type_employe='contractuel').count(),
            })
        
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def assigner_chef(self, request, pk=None):
        """Assigner un chef de service (Admin RH seulement)"""
        if request.user.role != 'admin_rh':
            return Response({'error': 'Permission refusée'}, status=403)
        
        service = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            chef = User.objects.get(id=user_id)
            if not chef.role.startswith('chef_'):
                return Response({'error': 'L\'utilisateur doit avoir un rôle de chef'}, status=400)
            
            service.chef_service = chef
            service.save()
            
            return Response({'message': f'Chef {chef.get_full_name()} assigné au service {service.nom}'})
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=404)

class PersonneViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les personnes avec filtrage hiérarchique
    """
    queryset = Personne.objects.all()
    serializer_class = PersonneSerializer
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_employe', 'service', 'genre', 'nationalite', 'situation_familiale']
    search_fields = ['nom', 'prenom', 'nni', 'fonction']
    ordering_fields = ['nom', 'prenom', 'date_naissance']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Personne.objects.none()
            
        if user.role == 'admin_rh':
            return Personne.objects.all()
        elif user.role.startswith('chef_'):
            # Chef ne voit que son service
            try:
                service = Service.objects.get(chef_service=user)
                return Personne.objects.filter(service=service)
            except Service.DoesNotExist:
                return Personne.objects.none()
        else:
            # Employé ne voit que lui-même
            return Personne.objects.filter(user=user)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PersonneDetailSerializer
        return PersonneSerializer
    
    def perform_create(self, serializer):
        user = self.request.user
        
        # Validation : chef ne peut créer que dans son service
        if user.role.startswith('chef_'):
            try:
                service = Service.objects.get(chef_service=user)
                serializer.save(service=service)
            except Service.DoesNotExist:
                raise ValidationError("Service non trouvé pour ce chef")
        else:
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def mon_profil(self, request):
        """Profile de l'utilisateur connecté"""
        try:
            personne = Personne.objects.get(user=request.user)
            serializer = PersonneDetailSerializer(personne)
            return Response(serializer.data)
        except Personne.DoesNotExist:
            return Response({'error': 'Profil non trouvé'}, status=404)
    
    @action(detail=False, methods=['get'])
    def par_service(self, request):
        """Grouper les employés par service"""
        queryset = self.get_queryset()
        
        services_data = {}
        for personne in queryset:
            service_name = personne.service.nom if personne.service else 'Sans service'
            if service_name not in services_data:
                services_data[service_name] = {
                    'service_info': {
                        'id': personne.service.id if personne.service else None,
                        'nom': service_name,
                        'type_service': personne.service.type_service if personne.service else None
                    },
                    'employes': []
                }
            services_data[service_name]['employes'].append(PersonneSerializer(personne).data)
        
        return Response(services_data)
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        """Statistiques des employés selon permissions"""
        queryset = self.get_queryset()
        
        total = queryset.count()
        par_genre = queryset.values('genre').annotate(count=Count('id'))
        par_type = queryset.values('type_employe').annotate(count=Count('id'))
        par_service = queryset.values('service__nom').annotate(count=Count('id'))
        par_nationalite = queryset.values('nationalite').annotate(count=Count('id'))
        
        return Response({
            'total': total,
            'par_genre': list(par_genre),
            'par_type_employe': list(par_type),
            'par_service': list(par_service),
            'par_nationalite': list(par_nationalite)
        })

class EnseignantViewSet(viewsets.ModelViewSet):
    """ViewSet pour les enseignants avec hiérarchie"""
    serializer_class = EnseignantSerializer
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['corps', 'grade', 'echelon']
    search_fields = ['personne__nom', 'personne__prenom', 'corps', 'grade']
    ordering_fields = ['personne__nom', 'grade', 'indice']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Enseignant.objects.none()
            
        if user.role == 'admin_rh':
            return Enseignant.objects.select_related('personne').all()
        elif user.role == 'chef_enseignant':
            # Chef enseignant voit tous les enseignants de son service
            try:
                service = Service.objects.get(chef_service=user, type_service='enseignant')
                return Enseignant.objects.filter(personne__service=service).select_related('personne')
            except Service.DoesNotExist:
                return Enseignant.objects.none()
        else:
            # Employé ne voit que lui-même
            return Enseignant.objects.filter(personne__user=user).select_related('personne')
    
    @action(detail=False, methods=['get'])
    def par_grade(self, request):
        """Statistiques des enseignants par grade selon permissions"""
        queryset = self.get_queryset()
        stats = queryset.values('grade').annotate(count=Count('id'))
        return Response(list(stats))
    
    @action(detail=False, methods=['get'])
    def fins_service_proche(self, request):
        """Enseignants dont la fin de service obligatoire approche"""
        queryset = self.get_queryset()
        date_limite = timezone.now().date() + timedelta(days=365)  # Dans 1 an
        
        enseignants = queryset.filter(
            date_fin_service_obligatoire__lte=date_limite,
            date_fin_service_obligatoire__gte=timezone.now().date()
        )
        
        serializer = self.get_serializer(enseignants, many=True)
        return Response(serializer.data)

class PersonnelPATViewSet(viewsets.ModelViewSet):
    """ViewSet pour le personnel PAT avec hiérarchie"""
    serializer_class = PersonnelPATSerializer
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['grade', 'poste']
    search_fields = ['personne__nom', 'personne__prenom', 'grade']
    ordering_fields = ['personne__nom', 'grade', 'indice']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return PersonnelPAT.objects.none()
            
        if user.role == 'admin_rh':
            return PersonnelPAT.objects.select_related('personne').all()
        elif user.role == 'chef_pat':
            try:
                service = Service.objects.get(chef_service=user, type_service='pat')
                return PersonnelPAT.objects.filter(personne__service=service).select_related('personne')
            except Service.DoesNotExist:
                return PersonnelPAT.objects.none()
        else:
            return PersonnelPAT.objects.filter(personne__user=user).select_related('personne')
    
    @action(detail=False, methods=['get'])
    def par_poste(self, request):
        """Statistiques du personnel PAT par poste"""
        queryset = self.get_queryset()
        stats = queryset.values('poste').annotate(count=Count('id'))
        return Response(list(stats))

class ContractuelViewSet(viewsets.ModelViewSet):
    """ViewSet pour les contractuels avec hiérarchie"""
    serializer_class = ContractuelSerializer
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_contrat']
    search_fields = ['personne__nom', 'personne__prenom']
    ordering_fields = ['personne__nom', 'date_debut_contrat']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Contractuel.objects.none()
            
        if user.role == 'admin_rh':
            return Contractuel.objects.select_related('personne').all()
        elif user.role == 'chef_contractuel':
            try:
                service = Service.objects.get(chef_service=user, type_service='contractuel')
                return Contractuel.objects.filter(personne__service=service).select_related('personne')
            except Service.DoesNotExist:
                return Contractuel.objects.none()
        else:
            return Contractuel.objects.filter(personne__user=user).select_related('personne')
    
    @action(detail=False, methods=['get'])
    def expires_bientot(self, request):
        """Contrats qui expirent dans les 30 prochains jours selon permissions"""
        queryset = self.get_queryset()
        date_limite = timezone.now().date() + timedelta(days=30)
        
        contrats = queryset.filter(
            date_fin_contrat__lte=date_limite,
            date_fin_contrat__gte=timezone.now().date()
        )
        
        serializer = self.get_serializer(contrats, many=True)
        return Response(serializer.data)


# ========================================
# VIEWSETS EXISTANTS ADAPTÉS
# ========================================

class StructureViewSet(viewsets.ModelViewSet):
    queryset = Structure.objects.all()
    serializer_class = StructureSerializer
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_structure', 'parent_structure', 'service']
    search_fields = ['nom', 'description']
    ordering_fields = ['nom', 'type_structure']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Structure.objects.none()
            
        if user.role == 'admin_rh':
            return Structure.objects.all()
        elif user.role.startswith('chef_'):
            try:
                service = Service.objects.get(chef_service=user)
                return Structure.objects.filter(service=service)
            except Service.DoesNotExist:
                return Structure.objects.none()
        else:
            if hasattr(user, 'personne') and user.personne.service:
                return Structure.objects.filter(service=user.personne.service)
        
        return Structure.objects.none()
    
    @action(detail=False, methods=['get'])
    def arborescence(self, request):
        """Retourne l'arborescence des structures selon permissions"""
        queryset = self.get_queryset()
        structures_racine = queryset.filter(parent_structure__isnull=True)
        serializer = StructureTreeSerializer(structures_racine, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def employes(self, request, pk=None):
        """Retourne tous les employés d'une structure"""
        structure = self.get_object()
        employes = Personne.objects.filter(structure=structure)
        
        # Filtrage selon permissions
        user = request.user
        if user.role != 'admin_rh':
            if structure.service and structure.service.chef_service != user:
                return Response({'error': 'Permission refusée'}, status=403)
        
        serializer = PersonneSerializer(employes, many=True)
        return Response(serializer.data)

class RecrutementViewSet(viewsets.ModelViewSet):
    queryset = Recrutement.objects.select_related('structure_recruteur', 'service_recruteur').all()
    serializer_class = RecrutementSerializer
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_employe', 'statut_offre', 'structure_recruteur', 'service_recruteur']
    search_fields = ['titre_poste', 'description']
    ordering_fields = ['date_limite', 'date_entree_prevue']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Recrutement.objects.none()
            
        if user.role == 'admin_rh':
            return self.queryset
        elif user.role.startswith('chef_'):
            try:
                service = Service.objects.get(chef_service=user)
                return self.queryset.filter(service_recruteur=service)
            except Service.DoesNotExist:
                return Recrutement.objects.none()
        else:
            # Employé peut voir les recrutements de son service
            if hasattr(user, 'personne') and user.personne.service:
                return self.queryset.filter(service_recruteur=user.personne.service)
        
        return Recrutement.objects.none()

class CandidatViewSet(viewsets.ModelViewSet):
    queryset = Candidat.objects.select_related('recrutement').all()
    serializer_class = CandidatSerializer
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['statut_candidature', 'recrutement']
    search_fields = ['nom', 'prenom', 'email']
    ordering_fields = ['date_candidature', 'nom']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Candidat.objects.none()
            
        if user.role == 'admin_rh':
            return self.queryset
        elif user.role.startswith('chef_'):
            try:
                service = Service.objects.get(chef_service=user)
                return self.queryset.filter(recrutement__service_recruteur=service)
            except Service.DoesNotExist:
                return Candidat.objects.none()
        
        return Candidat.objects.none()

class AbsenceViewSet(viewsets.ModelViewSet):
    queryset = Absence.objects.select_related('personne').all()
    serializer_class = AbsenceSerializer
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_absence', 'statut', 'personne']
    search_fields = ['personne__nom', 'personne__prenom']
    ordering_fields = ['date_debut', 'date_demande_absence']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Absence.objects.none()
            
        if user.role == 'admin_rh':
            return self.queryset
        elif user.role.startswith('chef_'):
            try:
                service = Service.objects.get(chef_service=user)
                return self.queryset.filter(personne__service=service)
            except Service.DoesNotExist:
                return Absence.objects.none()
        else:
            return self.queryset.filter(personne__user=user)
    
    @action(detail=False, methods=['get'])
    def en_cours(self, request):
        """Absences en cours selon permissions"""
        queryset = self.get_queryset()
        aujourd_hui = timezone.now().date()
        
        absences = queryset.filter(
            date_debut__lte=aujourd_hui,
            date_fin__gte=aujourd_hui,
            statut='APPROUVÉ'
        )
        
        serializer = self.get_serializer(absences, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def en_attente_approbation(self, request):
        """Absences en attente d'approbation pour les chefs"""
        user = request.user
        
        if not user.role.startswith('chef_') and user.role != 'admin_rh':
            return Response({'error': 'Permission refusée'}, status=403)
        
        queryset = self.get_queryset()
        absences = queryset.filter(statut='EN_ATTENTE')
        
        serializer = self.get_serializer(absences, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approuver(self, request, pk=None):
        """Approuver une absence (Chef de service ou Admin RH)"""
        absence = self.get_object()
        user = request.user
        
        # Vérifier les permissions d'approbation
        if not absence.peut_approuver(user):
            return Response({'error': 'Permission refusée pour approuver cette absence'}, status=403)
        
        absence.statut = 'APPROUVÉ'
        absence.approuve_par = user
        absence.commentaire_approbateur = request.data.get('commentaire', '')
        absence.save()
        
        return Response({'message': 'Absence approuvée avec succès'})
    
    @action(detail=True, methods=['post'])
    def refuser(self, request, pk=None):
        """Refuser une absence"""
        absence = self.get_object()
        user = request.user
        
        if not absence.peut_approuver(user):
            return Response({'error': 'Permission refusée'}, status=403)
        
        motif_refus = request.data.get('motif_refus', '')
        if not motif_refus:
            return Response({'error': 'Motif de refus requis'}, status=400)
        
        absence.statut = 'REFUSÉ'
        absence.approuve_par = user
        absence.motif_refus = motif_refus
        absence.save()
        
        return Response({'message': 'Absence refusée'})
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        """Statistiques des absences selon permissions"""
        queryset = self.get_queryset()
        stats = queryset.values('type_absence').annotate(count=Count('id'))
        par_statut = queryset.values('statut').annotate(count=Count('id'))
        
        return Response({
            'par_type': list(stats),
            'par_statut': list(par_statut),
            'total': queryset.count()
        })

class PaieViewSet(viewsets.ModelViewSet):
    queryset = Paie.objects.select_related('personne').all()
    serializer_class = PaieSerializer
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['statut_paiement', 'mois_annee', 'personne']
    search_fields = ['personne__nom', 'personne__prenom']
    ordering_fields = ['date_paiement', 'mois_annee']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Paie.objects.none()
            
        if user.role == 'admin_rh':
            return self.queryset
        elif user.role.startswith('chef_'):
            try:
                service = Service.objects.get(chef_service=user)
                return self.queryset.filter(personne__service=service)
            except Service.DoesNotExist:
                return Paie.objects.none()
        else:
            return self.queryset.filter(personne__user=user)
    
    @action(detail=False, methods=['get'])
    def resume_mensuel(self, request):
        """Résumé des paies par mois selon permissions"""
        mois = request.query_params.get('mois')
        if not mois:
            return Response({'error': 'Paramètre mois requis (format: YYYY-MM)'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.get_queryset()
        paies = queryset.filter(mois_annee=mois)
        
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
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['structure_origine', 'structure_detachement', 'personne', 'statut']
    search_fields = ['personne__nom', 'personne__prenom']
    ordering_fields = ['date_debut_detachement', 'date_fin_detachement']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Detachement.objects.none()
            
        if user.role == 'admin_rh':
            return self.queryset
        elif user.role.startswith('chef_'):
            try:
                service = Service.objects.get(chef_service=user)
                # Détachements concernant le service (sortants ou entrants)
                return self.queryset.filter(
                    Q(structure_origine__service=service) | 
                    Q(structure_detachement__service=service) |
                    Q(personne__service=service)
                )
            except Service.DoesNotExist:
                return Detachement.objects.none()
        else:
            return self.queryset.filter(personne__user=user)

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.select_related('proprietaire').all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_document', 'proprietaire']
    search_fields = ['nom', 'proprietaire__nom', 'proprietaire__prenom']
    ordering_fields = ['date_upload', 'nom']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Document.objects.none()
            
        if user.role == 'admin_rh':
            return self.queryset
        elif user.role.startswith('chef_'):
            try:
                service = Service.objects.get(chef_service=user)
                return self.queryset.filter(proprietaire__service=service)
            except Service.DoesNotExist:
                return Document.objects.none()
        else:
            return self.queryset.filter(proprietaire__user=user)
    
    @action(detail=False, methods=['get'])
    def mes_documents(self, request):
        """Documents de l'utilisateur connecté"""
        try:
            personne = Personne.objects.get(user=request.user)
            documents = Document.objects.filter(proprietaire=personne)
            serializer = self.get_serializer(documents, many=True)
            return Response(serializer.data)
        except Personne.DoesNotExist:
            return Response([])


# ========================================
# VIEWSETS D'ÉNUMÉRATION (PERMISSIONS OUVERTES)
# ========================================

class StatutOffreViewSet(viewsets.ModelViewSet):
    queryset = StatutOffre.objects.all()
    serializer_class = StatutOffreSerializer
    permission_classes = [AllowAny]

class TypeStructureViewSet(viewsets.ModelViewSet):
    queryset = TypeStructure.objects.all()
    serializer_class = TypeStructureSerializer
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


# ========================================
# VIEWSETS SPÉCIAUX POUR DASHBOARD
# ========================================

class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet spécial pour les données du dashboard selon le rôle
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def admin_rh(self, request):
        """Dashboard Admin RH - Vue globale"""
        if request.user.role != 'admin_rh':
            return Response({'error': 'Permission refusée'}, status=403)
        
        # Statistiques globales
        total_employes = Personne.objects.count()
        total_services = Service.objects.count()
        
        # Par service
        stats_services = []
        for service in Service.objects.all():
            stats_services.append({
                'nom': service.nom,
                'type': service.type_service,
                'chef': service.chef_service.get_full_name() if service.chef_service else 'Non assigné',
                'nombre_employes': service.employes.count()
            })
        
        # Absences en attente
        absences_attente = Absence.objects.filter(statut='EN_ATTENTE').count()
        
        # Contrats expirant bientôt
        date_limite = timezone.now().date() + timedelta(days=30)
        contrats_expirant = Contractuel.objects.filter(
            date_fin_contrat__lte=date_limite,
            date_fin_contrat__gte=timezone.now().date()
        ).count()
        
        return Response({
            'statistiques_generales': {
                'total_employes': total_employes,
                'total_services': total_services,
                'absences_en_attente': absences_attente,
                'contrats_expirant_bientot': contrats_expirant
            },
            'services': stats_services,
            'role': 'admin_rh'
        })
    
    @action(detail=False, methods=['get'])
    def chef_service(self, request):
        """Dashboard Chef de Service - Vue limitée à son service"""
        user = request.user
        
        if not user.role.startswith('chef_'):
            return Response({'error': 'Permission refusée'}, status=403)
        
        try:
            service = Service.objects.get(chef_service=user)
            
            # Statistiques du service
            employes = service.employes.all()
            total_employes = employes.count()
            
            # Absences en attente dans son service
            absences_attente = Absence.objects.filter(
                personne__service=service,
                statut='EN_ATTENTE'
            ).count()
            
            # Répartition par type d'employé
            repartition = employes.values('type_employe').annotate(count=Count('id'))
            
            # Contrats expirant (si service contractuel)
            contrats_expirant = 0
            if service.type_service == 'contractuel':
                date_limite = timezone.now().date() + timedelta(days=30)
                contrats_expirant = Contractuel.objects.filter(
                    personne__service=service,
                    date_fin_contrat__lte=date_limite,
                    date_fin_contrat__gte=timezone.now().date()
                ).count()
            
            return Response({
                'service_info': {
                    'nom': service.nom,
                    'type': service.type_service,
                    'description': service.description
                },
                'statistiques': {
                    'total_employes': total_employes,
                    'absences_en_attente': absences_attente,
                    'contrats_expirant_bientot': contrats_expirant,
                    'repartition_employes': list(repartition)
                },
                'role': user.role
            })
            
        except Service.DoesNotExist:
            return Response({'error': 'Service non trouvé pour ce chef'}, status=404)
    
    @action(detail=False, methods=['get'])
    def employe(self, request):
        """Dashboard Employé - Vue personnelle"""
        user = request.user
        
        if user.role != 'employe':
            return Response({'error': 'Permission refusée'}, status=403)
        
        try:
            personne = Personne.objects.get(user=user)
            
            # Mes absences récentes
            mes_absences = Absence.objects.filter(personne=personne).order_by('-date_demande_absence')[:5]
            
            # Mes documents
            mes_documents = Document.objects.filter(proprietaire=personne).count()
            
            # Ma paie du mois en cours
            mois_actuel = timezone.now().strftime('%Y-%m')
            ma_paie = None
            try:
                ma_paie = Paie.objects.get(personne=personne, mois_annee=mois_actuel)
            except Paie.DoesNotExist:
                pass
            
            return Response({
                'profil': {
                    'nom_complet': f"{personne.prenom} {personne.nom}",
                    'fonction': personne.fonction,
                    'service': personne.service.nom if personne.service else None,
                    'type_employe': personne.type_employe
                },
                'statistiques': {
                    'nombre_absences': mes_absences.count(),
                    'nombre_documents': mes_documents
                },
                'absences_recentes': AbsenceSerializer(mes_absences, many=True).data,
                'paie_courante': PaieSerializer(ma_paie).data if ma_paie else None,
                'role': 'employe'
            })
            
        except Personne.DoesNotExist:
            return Response({'error': 'Profil employé non trouvé'}, status=404)
    
    @action(detail=False, methods=['get'])
    def auto(self, request):
        """Dashboard automatique selon le rôle"""
        user = request.user
        
        if user.role == 'admin_rh':
            return self.admin_rh(request)
        elif user.role.startswith('chef_'):
            return self.chef_service(request)
        elif user.role == 'employe':
            return self.employe(request)
        else:
            return Response({'error': 'Rôle non reconnu'}, status=400)


# ========================================
# VIEWSET POUR GESTION DES PERMISSIONS
# ========================================

class PermissionViewSet(viewsets.ViewSet):
    """
    ViewSet pour tester et gérer les permissions
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def mes_permissions(self, request):
        """Retourne les permissions de l'utilisateur connecté"""
        user = request.user
        
        permissions = {
            'user_id': user.id,
            'username': user.username,
            'role': getattr(user, 'role', 'employe'),
            'permissions': []
        }
        
        # Définir les permissions selon le rôle
        if user.role == 'admin_rh':
            permissions['permissions'] = [
                'view_all', 'add_all', 'change_all', 'delete_all', 
                'approve_all', 'manage_users', 'assign_roles'
            ]
        elif user.role.startswith('chef_'):
            permissions['permissions'] = [
                'view_service', 'add_employe_service', 'change_employe_service',
                'approve_absence_service', 'view_paie_service'
            ]
        else:
            permissions['permissions'] = [
                'view_self', 'change_self', 'request_absence', 'view_own_paie'
            ]
        
        # Ajouter info sur le service si applicable
        if hasattr(user, 'personne') and user.personne.service:
            permissions['service'] = {
                'id': user.personne.service.id,
                'nom': user.personne.service.nom,
                'type': user.personne.service.type_service
            }
        elif user.role.startswith('chef_'):
            try:
                service = Service.objects.get(chef_service=user)
                permissions['service'] = {
                    'id': service.id,
                    'nom': service.nom,
                    'type': service.type_service
                }
            except Service.DoesNotExist:
                permissions['service'] = None
        
        return Response(permissions)
    
    @action(detail=False, methods=['get'])
    def test_hierarchie(self, request):
        """Endpoint de test pour vérifier la hiérarchie"""
        user = request.user
        
        # Test des accès selon le rôle
        test_results = {
            'user_role': user.role,
            'access_tests': {}
        }
        
        # Test accès aux personnes
        personnes_count = PersonneViewSet().get_queryset().count()
        test_results['access_tests']['personnes_visibles'] = personnes_count
        
        # Test accès aux services
        services_count = ServiceViewSet().get_queryset().count()
        test_results['access_tests']['services_visibles'] = services_count
        
        # Test accès aux absences
        absences_count = AbsenceViewSet().get_queryset().count()
        test_results['access_tests']['absences_visibles'] = absences_count
        
        return Response(test_results)