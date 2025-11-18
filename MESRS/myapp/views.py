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
from django.conf import settings

# Ajoutez cette ligne avec les autres imports
from calendar import monthrange

from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
import json
from calendar import monthrange
import csv
from io import StringIO

from django.utils import timezone
from datetime import timedelta
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
    """ViewSet pour les enseignants avec hiérarchie CORRIGÉ"""
    serializer_class = EnseignantSerializer
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['corps', 'grade', 'echelon']
    search_fields = ['personne__nom', 'personne__prenom', 'corps', 'grade']
    ordering_fields = ['personne__nom', 'grade', 'indice']
    
    def get_queryset(self):
        user = self.request.user
        
        print(f"🔍 EnseignantViewSet.get_queryset() appelé pour: {user.username} (rôle: {getattr(user, 'role', 'AUCUN')})")
        
        if not user.is_authenticated:
            print("❌ Utilisateur non authentifié")
            return Enseignant.objects.none()
            
        # ✅ CORRECTION: Vérifier que l'attribut 'role' existe
        if not hasattr(user, 'role'):
            print("❌ Utilisateur sans rôle défini")
            return Enseignant.objects.none()
            
        if user.role == 'admin_rh':
            print("✅ Admin RH - Accès à tous les enseignants")
            return Enseignant.objects.select_related('personne', 'personne__service').all()
            
        elif user.role == 'chef_enseignant':
            print("🎓 Chef enseignant - Recherche de son service...")
            try:
                # ✅ CORRECTION: Import ici pour éviter les imports circulaires
                from .models import Service
                service = Service.objects.get(chef_service=user, type_service='enseignant')
                queryset = Enseignant.objects.filter(personne__service=service).select_related('personne', 'personne__service')
                print(f"✅ Service trouvé: {service.nom} - {queryset.count()} enseignants")
                return queryset
            except Service.DoesNotExist:
                print(f"❌ Aucun service 'enseignant' trouvé pour le chef {user.username}")
                return Enseignant.objects.none()
            except Exception as e:
                print(f"❌ Erreur inattendue: {e}")
                return Enseignant.objects.none()
        else:
            # Employé ne voit que lui-même s'il est enseignant
            print("👤 Employé - Accès à son propre profil")
            try:
                return Enseignant.objects.filter(personne__user=user).select_related('personne')
            except Exception as e:
                print(f"❌ Erreur pour employé: {e}")
                return Enseignant.objects.none()
    
    def list(self, request, *args, **kwargs):
        """Override pour debugging"""
        print(f"📋 Liste des enseignants demandée par {request.user.username}")
        
        try:
            queryset = self.get_queryset()
            print(f"📊 Queryset contient {queryset.count()} enseignants")
            
            # Appliquer les filtres
            queryset = self.filter_queryset(queryset)
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            print(f"✅ Retour de {len(serializer.data)} enseignants")
            return Response(serializer.data)
            
        except Exception as e:
            print(f"❌ Erreur dans list(): {e}")
            return Response({
                'error': f'Erreur lors de la récupération des enseignants: {str(e)}',
                'debug_info': {
                    'user': request.user.username,
                    'role': getattr(request.user, 'role', 'AUCUN'),
                    'authenticated': request.user.is_authenticated
                }
            }, status=500)
    
    def create(self, request, *args, **kwargs):
        """Création d'enseignant avec vérifications"""
        user = request.user
        print(f"➕ Création d'enseignant par {user.username}")
        
        if user.role not in ['admin_rh', 'chef_enseignant']:
            return Response({'error': 'Permission refusée pour créer un enseignant'}, status=403)
        
        # Si c'est un chef, vérifier qu'il crée dans son service
        if user.role == 'chef_enseignant':
            try:
                from .models import Service
                service = Service.objects.get(chef_service=user, type_service='enseignant')
                # Assurer que la personne est assignée au bon service
                if 'personne' in request.data and 'service' in request.data['personne']:
                    if request.data['personne']['service'] != service.id:
                        return Response({'error': 'Vous ne pouvez créer que dans votre service'}, status=403)
            except Service.DoesNotExist:
                return Response({'error': 'Service enseignant non trouvé'}, status=404)
        
        return super().create(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def debug_info(self, request):
        """Endpoint de debug amélioré"""
        user = request.user
        
        debug_data = {
            'timestamp': timezone.now().isoformat(),
            'user_info': {
                'id': user.id,
                'username': user.username,
                'role': getattr(user, 'role', 'AUCUN RÔLE'),
                'is_authenticated': user.is_authenticated,
                'is_active': user.is_active
            },
            'queryset_info': {},
            'service_info': None,
            'permissions': []
        }
        
        try:
            # Test du queryset
            queryset = self.get_queryset()
            debug_data['queryset_info'] = {
                'count': queryset.count(),
                'exists': queryset.exists(),
                'sql_query': str(queryset.query) if queryset.exists() else 'EMPTY QUERYSET'
            }
            
            # Informations sur le service si chef
            if user.role == 'chef_enseignant':
                try:
                    from .models import Service
                    service = Service.objects.get(chef_service=user, type_service='enseignant')
                    debug_data['service_info'] = {
                        'id': service.id,
                        'nom': service.nom,
                        'type': service.type_service,
                        'total_employes': service.employes.count(),
                        'enseignants_count': service.employes.filter(type_employe='enseignant').count()
                    }
                except Service.DoesNotExist:
                    debug_data['service_info'] = 'SERVICE_NOT_FOUND'
            
            # Permissions
            debug_data['permissions'] = [
                f"Can view: {self.permission_classes[0]().has_permission(request, self)}",
                f"User role: {user.role}",
                f"Is admin_rh: {user.role == 'admin_rh'}",
                f"Is chef_enseignant: {user.role == 'chef_enseignant'}"
            ]
            
        except Exception as e:
            debug_data['error'] = str(e)
            debug_data['traceback'] = str(e.__class__.__name__)
        
        return Response(debug_data)
    
    
    @action(detail=False, methods=['get'])
    def par_grade(self, request):
            """Statistiques par grade CORRIGÉ"""
            try:
                queryset = self.get_queryset()
                
                if not queryset.exists():
                    return Response({
                        'message': 'Aucun enseignant trouvé',
                        'data': [],
                        'total': 0
                    })
                
                # ✅ CORRECTION: Utiliser 'personne' au lieu de 'id'
                stats_data = queryset.values('grade').annotate(count=Count('personne'))
                
                # Formater la réponse avec les labels
                data = []
                for stat in stats_data:
                    grade = stat['grade']
                    count = stat['count']
                    
                    # Obtenir le label depuis les choices du modèle
                    grade_label = dict(Enseignant.GRADE_CHOICES).get(grade, grade)
                    
                    data.append({
                        'grade': grade,
                        'count': count,
                        'label': grade_label
                    })
                
                return Response({
                    'data': data,
                    'total': queryset.count(),
                    'success': True
                })
                
            except Exception as e:
                print(f"❌ Erreur par_grade: {str(e)}")
                return Response({
                    'error': str(e),
                    'success': False
                }, status=500)

    @action(detail=False, methods=['get'])
    def rapport_mensuel(self, request):
        """Rapport mensuel des enseignants pour chef de service"""
        user = request.user
        
        if user.role != 'chef_enseignant':
            return Response({'error': 'Permission refusée'}, status=403)
        
        # Paramètres
        mois = request.query_params.get('mois', timezone.now().strftime('%Y-%m'))
        
        try:
            # Récupérer le service du chef
            service = Service.objects.get(chef_service=user, type_service='enseignant')
            queryset = self.get_queryset()
            
            # Protection: Filtrer seulement les enseignants avec personne
            queryset = queryset.filter(personne__isnull=False)
            
            # Statistiques générales
            total_enseignants = queryset.count()
            
            # ✅ CORRECTION: Utiliser 'personne' au lieu de 'id' pour compter
            par_grade = queryset.values('grade').annotate(count=Count('personne'))
            
            # Dates du mois
            debut_mois = datetime.strptime(f"{mois}-01", '%Y-%m-%d').date()
            _, last_day = monthrange(debut_mois.year, debut_mois.month)
            fin_mois = debut_mois.replace(day=last_day)
            
            # Absences du mois
            absences_mois = Absence.objects.filter(
                personne__service=service,
                date_debut__lte=fin_mois,
                date_fin__gte=debut_mois
            ).values('type_absence').annotate(count=Count('id'))
            
            # Enseignants avec absences
            enseignants_avec_absences = queryset.filter(
                personne__absences__date_debut__lte=fin_mois,
                personne__absences__date_fin__gte=debut_mois
            ).distinct().count()
            
            # Taux de présence
            taux_presence = ((total_enseignants - enseignants_avec_absences) / total_enseignants * 100) if total_enseignants > 0 else 100
            
            # Absences par statut
            absences_par_statut = Absence.objects.filter(
                personne__service=service,
                date_debut__lte=fin_mois,
                date_fin__gte=debut_mois
            ).values('statut').annotate(count=Count('id'))
            
            # Top 5 enseignants avec le plus d'absences
            top_absences = []
            for enseignant in queryset:
                if enseignant.personne:
                    nb_absences = Absence.objects.filter(
                        personne=enseignant.personne,
                        date_debut__lte=fin_mois,
                        date_fin__gte=debut_mois
                    ).count()
                    if nb_absences > 0:
                        top_absences.append({
                            'nom': f"{enseignant.personne.prenom} {enseignant.personne.nom}",
                            'grade': enseignant.grade,
                            'nombre_absences': nb_absences
                        })
            
            top_absences.sort(key=lambda x: x['nombre_absences'], reverse=True)
            top_absences = top_absences[:5]
            
            rapport = {
                'periode': mois,
                'service': service.nom,
                'statistiques': {
                    'total_enseignants': total_enseignants,
                    'enseignants_presents': total_enseignants - enseignants_avec_absences,
                    'enseignants_absents': enseignants_avec_absences,
                    'taux_presence': round(taux_presence, 2)
                },
                'repartition_grade': list(par_grade),
                'absences_par_type': list(absences_mois),
                'absences_par_statut': list(absences_par_statut),
                'top_absences': top_absences,
                'genere_le': timezone.now().isoformat()
            }
            
            return Response(rapport)
            
        except Service.DoesNotExist:
            return Response({'error': 'Service non trouvé'}, status=404)
        except Exception as e:
            print(f"❌ Erreur rapport_mensuel: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({'error': f'Erreur interne: {str(e)}'}, status=500)

    @action(detail=False, methods=['get'])
    def rapport_annuel(self, request):
        """Rapport annuel des enseignants"""
        user = request.user
        
        if user.role != 'chef_enseignant':
            return Response({'error': 'Permission refusée'}, status=403)
        
        annee = int(request.query_params.get('annee', timezone.now().year))
        
        try:
            service = Service.objects.get(chef_service=user, type_service='enseignant')
            queryset = self.get_queryset()
            
            # Données par mois
            donnees_mensuelles = []
            mois_noms = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                        'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
            
            for mois in range(1, 13):
                debut = datetime(annee, mois, 1).date()
                _, last_day = monthrange(annee, mois)
                fin = datetime(annee, mois, last_day).date()
                
                absences = Absence.objects.filter(
                    personne__service=service,
                    date_debut__lte=fin,
                    date_fin__gte=debut
                ).count()
                
                # Absences par type pour ce mois
                absences_par_type = Absence.objects.filter(
                    personne__service=service,
                    date_debut__lte=fin,
                    date_fin__gte=debut
                ).values('type_absence').annotate(count=Count('id'))
                
                donnees_mensuelles.append({
                    'mois': mois,
                    'nom_mois': mois_noms[mois-1],
                    'nombre_absences': absences,
                    'absences_par_type': list(absences_par_type)
                })
            
            # Évolution des effectifs
            evolution_effectifs = []
            for mois in range(1, 13):
                effectif = queryset.count()  # Effectif actuel pour tous les mois
                evolution_effectifs.append({
                    'mois': mois,
                    'nom_mois': mois_noms[mois-1],
                    'effectif': effectif
                })
            
            # Statistiques annuelles
            total_absences_annee = sum(d['nombre_absences'] for d in donnees_mensuelles)
            mois_plus_absences = max(donnees_mensuelles, key=lambda x: x['nombre_absences'])
            mois_moins_absences = min(donnees_mensuelles, key=lambda x: x['nombre_absences'])
            
            # Tendances
            premier_trimestre = sum(d['nombre_absences'] for d in donnees_mensuelles[:3])
            deuxieme_trimestre = sum(d['nombre_absences'] for d in donnees_mensuelles[3:6])
            troisieme_trimestre = sum(d['nombre_absences'] for d in donnees_mensuelles[6:9])
            quatrieme_trimestre = sum(d['nombre_absences'] for d in donnees_mensuelles[9:12])
            
            rapport = {
                'annee': annee,
                'service': service.nom,
                'donnees_mensuelles': donnees_mensuelles,
                'evolution_effectifs': evolution_effectifs,
                'statistiques_annuelles': {
                    'total_absences': total_absences_annee,
                    'moyenne_mensuelle': round(total_absences_annee / 12, 2),
                    'mois_plus_absences': mois_plus_absences,
                    'mois_moins_absences': mois_moins_absences
                },
                'donnees_trimestrielles': [
                    {'trimestre': 'T1', 'absences': premier_trimestre},
                    {'trimestre': 'T2', 'absences': deuxieme_trimestre},
                    {'trimestre': 'T3', 'absences': troisieme_trimestre},
                    {'trimestre': 'T4', 'absences': quatrieme_trimestre}
                ],
                'genere_le': timezone.now().isoformat()
            }
            
            return Response(rapport)
            
        except Service.DoesNotExist:
            return Response({'error': 'Service non trouvé'}, status=404)

    @action(detail=False, methods=['get'])
    def planning_absences(self, request):
        """Planning des absences pour le mois"""
        user = request.user
        
        if user.role != 'chef_enseignant':
            return Response({'error': 'Permission refusée'}, status=403)
        
        # Paramètres
        mois = request.query_params.get('mois', timezone.now().strftime('%Y-%m'))
        
        try:
            service = Service.objects.get(chef_service=user, type_service='enseignant')
            
            # Dates du mois
            debut_mois = datetime.strptime(f"{mois}-01", '%Y-%m-%d').date()
            _, last_day = monthrange(debut_mois.year, debut_mois.month)
            fin_mois = debut_mois.replace(day=last_day)
            
            # Récupérer toutes les absences du mois
            absences = Absence.objects.filter(
                personne__service=service,
                date_debut__lte=fin_mois,
                date_fin__gte=debut_mois,
                statut__in=['APPROUVÉ', 'EN_ATTENTE']
            ).select_related('personne').order_by('date_debut')
            
            # Organiser par jour
            planning = {}
            current_date = debut_mois
            
            while current_date <= fin_mois:
                day_key = current_date.strftime('%Y-%m-%d')
                planning[day_key] = {
                    'date': day_key,
                    'jour_semaine': current_date.strftime('%A'),
                    'numero_jour': current_date.day,
                    'est_weekend': current_date.weekday() >= 5,
                    'absences': [],
                    'nombre_absents': 0
                }
                current_date += timedelta(days=1)
            
            # Remplir le planning avec les absences
            for absence in absences:
                current_date = max(absence.date_debut, debut_mois)
                end_date = min(absence.date_fin, fin_mois)
                
                while current_date <= end_date:
                    day_key = current_date.strftime('%Y-%m-%d')
                    if day_key in planning:
                        enseignant_data = {
                            'id': absence.id,
                            'enseignant_id': absence.personne.id,
                            'nom': absence.personne.nom,
                            'prenom': absence.personne.prenom,
                            'nom_complet': f"{absence.personne.prenom} {absence.personne.nom}",
                            'grade': absence.personne.enseignant.grade if hasattr(absence.personne, 'enseignant') else 'N/A',
                            'type_absence': absence.type_absence,
                            'statut': absence.statut,
                            'debut': absence.date_debut.isoformat(),
                            'fin': absence.date_fin.isoformat(),
                            'duree_totale': (absence.date_fin - absence.date_debut).days + 1
                        }
                        planning[day_key]['absences'].append(enseignant_data)
                    current_date += timedelta(days=1)
            
            # Calculer le nombre d'absents par jour
            for day_data in planning.values():
                day_data['nombre_absents'] = len(day_data['absences'])
            
            # Statistiques du planning
            total_jours_ouvrables = sum(1 for day in planning.values() if not day['est_weekend'])
            total_absences_planifiees = absences.count()
            
            # Jour avec le plus d'absences
            jour_max_absences = max(planning.values(), key=lambda x: x['nombre_absents'])
            
            return Response({
                'mois': mois,
                'service': service.nom,
                'planning': planning,
                'statistiques': {
                    'total_absences': total_absences_planifiees,
                    'total_jours_ouvrables': total_jours_ouvrables,
                    'jour_max_absences': {
                        'date': jour_max_absences['date'],
                        'nombre': jour_max_absences['nombre_absents']
                    }
                }
            })
            
        except Service.DoesNotExist:
            return Response({'error': 'Service non trouvé'}, status=404)

    @action(detail=False, methods=['get'])
    def export_rapport(self, request):
        """Exporter le rapport en CSV ou JSON"""
        user = request.user
        
        if user.role != 'chef_enseignant':
            return Response({'error': 'Permission refusée'}, status=403)
        
        format_export = request.query_params.get('format', 'json')
        mois = request.query_params.get('mois', timezone.now().strftime('%Y-%m'))
        type_rapport = request.query_params.get('type', 'mensuel')
        
        try:
            service = Service.objects.get(chef_service=user, type_service='enseignant')
            queryset = self.get_queryset()
            
            # Dates du mois
            debut_mois = datetime.strptime(f"{mois}-01", '%Y-%m-%d').date()
            _, last_day = monthrange(debut_mois.year, debut_mois.month)
            fin_mois = debut_mois.replace(day=last_day)
            
            if type_rapport == 'detaille':
                # Rapport détaillé par enseignant
                donnees = []
                for enseignant in queryset:
                    absences = Absence.objects.filter(
                        personne=enseignant.personne,
                        date_debut__lte=fin_mois,
                        date_fin__gte=debut_mois
                    )
                    
                    total_jours_absence = sum((abs.date_fin - max(abs.date_debut, debut_mois)).days + 1 
                                            for abs in absences)
                    
                    donnees.append({
                        'nom': enseignant.personne.nom,
                        'prenom': enseignant.personne.prenom,
                        'grade': enseignant.grade,
                        'corps': enseignant.corps,
                        'indice': enseignant.indice,
                        'nombre_absences': absences.count(),
                        'jours_absence': total_jours_absence,
                        'types_absence': ', '.join(absences.values_list('type_absence', flat=True).distinct())
                    })
            else:
                # Rapport synthétique
                donnees = []
                for enseignant in queryset:
                    absences = Absence.objects.filter(
                        personne=enseignant.personne,
                        date_debut__lte=fin_mois,
                        date_fin__gte=debut_mois
                    )
                    
                    donnees.append({
                        'nom': enseignant.personne.nom,
                        'prenom': enseignant.personne.prenom,
                        'grade': enseignant.grade,
                        'nombre_absences': absences.count(),
                        'jours_absence': sum((abs.date_fin - abs.date_debut).days + 1 for abs in absences)
                    })
            
            if format_export == 'csv':
                output = StringIO()
                if donnees:
                    fieldnames = donnees[0].keys()
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(donnees)
                
                response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
                filename = f"rapport_enseignants_{type_rapport}_{mois}.csv"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            
            # Format JSON
            return Response({
                'donnees': donnees,
                'periode': mois,
                'service': service.nom,
                'type_rapport': type_rapport,
                'genere_le': timezone.now().isoformat()
            })
            
        except Service.DoesNotExist:
            return Response({'error': 'Service non trouvé'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        
class PersonnelPATViewSet(viewsets.ModelViewSet):
    """ViewSet pour le personnel PAT avec hiérarchie (miroir d'EnseignantViewSet)"""
    serializer_class = PersonnelPATSerializer
    permission_classes = [IsAdminRHOrChefService]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['grade', 'poste']
    search_fields = ['personne__nom', 'personne__prenom', 'grade', 'poste']
    ordering_fields = ['personne__nom', 'grade', 'indice']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return PersonnelPAT.objects.none()

        if user.role == 'admin_rh':
            return PersonnelPAT.objects.select_related('personne', 'personne__service')
        elif user.role == 'chef_pat':
            try:
                service = Service.objects.get(chef_service=user, type_service='pat')
                return PersonnelPAT.objects.filter(personne__service=service).select_related('personne', 'personne__service')
            except Service.DoesNotExist:
                return PersonnelPAT.objects.none()
        else:
            # Employé : juste lui-même s'il est PAT
            return PersonnelPAT.objects.filter(personne__user=user).select_related('personne', 'personne__service')

    # ---------- Stats simples ----------
    @action(detail=False, methods=['get'])
    def par_poste(self, request):
        """Répartition du PAT par poste (avec label)"""
        qs = self.get_queryset()
        # ✅ CORRECTION: Utiliser 'personne_id' au lieu de 'personne' pour Count
        raw = qs.values('poste').annotate(count=Count('personne_id'))
        choices = dict(PersonnelPAT.POSTE_CHOICES)
        data = [{'poste': r['poste'], 'label': choices.get(r['poste'], r['poste']), 'count': r['count']} for r in raw]
        return Response({'total': qs.count(), 'data': data})    

    # ---------- Debug (miroir Enseignant.debug_info) ----------
    @action(detail=False, methods=['get'])
    def debug_info(self, request):
        user = request.user
        info = {'user': user.username, 'role': getattr(user, 'role', 'N/A')}
        try:
            qs = self.get_queryset()
            info['queryset'] = {'count': qs.count(), 'sql': str(qs.query) if qs.exists() else 'EMPTY'}
            if user.role == 'chef_pat':
                service = Service.objects.get(chef_service=user, type_service='pat')
                info['service'] = {
                    'id': service.id, 'nom': service.nom, 'type': service.type_service,
                    'total_employes': service.employes.filter(type_employe='pat').count()
                }
        except Exception as e:
            info['error'] = str(e)
        return Response(info)

    # ---------- Rapport mensuel ----------
    @action(detail=False, methods=['get'])
    def rapport_mensuel(self, request):
        """Rapport mensuel PAT (absences, répartition par poste…)"""
        user = request.user
        if user.role != 'chef_pat':
            return Response({'error': 'Permission refusée'}, status=403)

        mois = request.query_params.get('mois', timezone.now().strftime('%Y-%m'))
        try:
            service = Service.objects.get(chef_service=user, type_service='pat')
            qs = self.get_queryset()

            # bornes du mois
            debut_mois = datetime.strptime(f"{mois}-01", "%Y-%m-%d").date()
            _, last = monthrange(debut_mois.year, debut_mois.month)
            fin_mois = debut_mois.replace(day=last)

            total_pat = qs.count()

            # répartition par poste
            par_poste = qs.values('poste').annotate(count=Count('personne'))
            # absences du mois
            absences_mois = Absence.objects.filter(
                personne__service=service,
                date_debut__lte=fin_mois,
                date_fin__gte=debut_mois
            ).values('type_absence').annotate(count=Count('id'))

            # nombre d’agents avec au moins une absence dans le mois
            agents_absents = qs.filter(
                personne__absences__date_debut__lte=fin_mois,
                personne__absences__date_fin__gte=debut_mois
            ).distinct().count()

            taux_presence = ((total_pat - agents_absents) / total_pat * 100) if total_pat else 100

            # top 5 absences
            top_abs = []
            for agent in qs:
                n = Absence.objects.filter(
                    personne=agent.personne,
                    date_debut__lte=fin_mois,
                    date_fin__gte=debut_mois
                ).count()
                if n > 0:
                    top_abs.append({
                        'nom': f"{agent.personne.prenom} {agent.personne.nom}",
                        'poste': agent.poste,
                        'nombre_absences': n
                    })
            top_abs.sort(key=lambda x: x['nombre_absences'], reverse=True)
            top_abs = top_abs[:5]

            return Response({
                'periode': mois,
                'service': service.nom,
                'statistiques': {
                    'total_pat': total_pat,
                    'agents_presents': total_pat - agents_absents,
                    'agents_absents': agents_absents,
                    'taux_presence': round(taux_presence, 2)
                },
                'repartition_poste': list(par_poste),
                'absences_par_type': list(absences_mois),
                'top_absences': top_abs,
                'genere_le': timezone.now().isoformat()
            })
        except Service.DoesNotExist:
            return Response({'error': 'Service non trouvé'}, status=404)

    # ---------- Rapport annuel ----------
    @action(detail=False, methods=['get'])
    def rapport_annuel(self, request):
        """Rapport annuel PAT (évolution absences, répartition par type, etc.)"""
        user = request.user
        if user.role != 'chef_pat':
            return Response({'error': 'Permission refusée'}, status=403)

        annee = int(request.query_params.get('annee', timezone.now().year))
        try:
            service = Service.objects.get(chef_service=user, type_service='pat')
            qs = self.get_queryset()

            mois_noms = ['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre']
            donnees = []
            for m in range(1, 12+1):
                debut = datetime(annee, m, 1).date()
                _, last = monthrange(annee, m)
                fin = datetime(annee, m, last).date()

                nb = Absence.objects.filter(
                    personne__service=service,
                    date_debut__lte=fin,
                    date_fin__gte=debut
                ).count()
                par_type = Absence.objects.filter(
                    personne__service=service,
                    date_debut__lte=fin,
                    date_fin__gte=debut
                ).values('type_absence').annotate(count=Count('id'))

                donnees.append({'mois': m, 'nom_mois': mois_noms[m-1], 'nombre_absences': nb, 'absences_par_type': list(par_type)})

            total = sum(d['nombre_absences'] for d in donnees)
            return Response({
                'annee': annee,
                'service': service.nom,
                'donnees_mensuelles': donnees,
                'statistiques_annuelles': {
                    'total_absences': total,
                    'moyenne_mensuelle': round(total/12, 2) if donnees else 0,
                    'mois_plus_absences': max(donnees, key=lambda x:x['nombre_absences']) if donnees else None,
                    'mois_moins_absences': min(donnees, key=lambda x:x['nombre_absences']) if donnees else None
                },
                'genere_le': timezone.now().isoformat()
            })
        except Service.DoesNotExist:
            return Response({'error': 'Service non trouvé'}, status=404)

    # ---------- Planning des absences (mois) ----------
    @action(detail=False, methods=['get'])
    def planning_absences(self, request):
        user = request.user
        if user.role != 'chef_pat':
            return Response({'error': 'Permission refusée'}, status=403)

        mois = request.query_params.get('mois', timezone.now().strftime('%Y-%m'))
        try:
            service = Service.objects.get(chef_service=user, type_service='pat')
            debut_mois = datetime.strptime(f"{mois}-01", "%Y-%m-%d").date()
            _, last = monthrange(debut_mois.year, debut_mois.month)
            fin_mois = debut_mois.replace(day=last)

            absences = Absence.objects.filter(
                personne__service=service,
                date_debut__lte=fin_mois,
                date_fin__gte=debut_mois,
                statut__in=['APPROUVÉ', 'EN_ATTENTE']
            ).select_related('personne')

            # calendrier
            planning = {}
            cur = debut_mois
            while cur <= fin_mois:
                key = cur.strftime('%Y-%m-%d')
                planning[key] = {
                    'date': key,
                    'jour_semaine': cur.strftime('%A'),
                    'numero_jour': cur.day,
                    'est_weekend': cur.weekday() >= 5,
                    'absences': [],
                    'nombre_absents': 0
                }
                cur += timedelta(days=1)

            for a in absences:
                start = max(a.date_debut, debut_mois)
                end = min(a.date_fin, fin_mois)
                cur = start
                while cur <= end:
                    key = cur.strftime('%Y-%m-%d')
                    if key in planning:
                        planning[key]['absences'].append({
                            'id': a.id,
                            'agent_id': a.personne.id,
                            'nom_complet': f"{a.personne.prenom} {a.personne.nom}",
                            'poste': getattr(getattr(a.personne, 'personnelpat', None), 'poste', 'N/A'),
                            'type_absence': a.type_absence,
                            'statut': a.statut,
                            'debut': a.date_debut.isoformat(),
                            'fin': a.date_fin.isoformat()
                        })
                    cur += timedelta(days=1)

            for d in planning.values():
                d['nombre_absents'] = len(d['absences'])

            jour_max = max(planning.values(), key=lambda x: x['nombre_absents']) if planning else None
            return Response({
                'mois': mois,
                'service': service.nom,
                'planning': planning,
                'statistiques': {
                    'total_absences': absences.count(),
                    'jour_max_absences': {'date': jour_max['date'], 'nombre': jour_max['nombre_absents']} if jour_max else None
                }
            })
        except Service.DoesNotExist:
            return Response({'error': 'Service non trouvé'}, status=404)

    # ---------- Export (json/csv) ----------
    @action(detail=False, methods=['get'])
    def export_rapport(self, request):
        user = request.user
        if user.role != 'chef_pat':
            return Response({'error': 'Permission refusée'}, status=403)

        format_export = request.query_params.get('format', 'json')
        mois = request.query_params.get('mois', timezone.now().strftime('%Y-%m'))
        type_rapport = request.query_params.get('type', 'mensuel')

        try:
            service = Service.objects.get(chef_service=user, type_service='pat')
            qs = self.get_queryset()

            debut_mois = datetime.strptime(f"{mois}-01", "%Y-%m-%d").date()
            _, last = monthrange(debut_mois.year, debut_mois.month)
            fin_mois = debut_mois.replace(day=last)

            # vue synthétique/détaillée
            donnees = []
            for agent in qs:
                absences = Absence.objects.filter(
                    personne=agent.personne,
                    date_debut__lte=fin_mois,
                    date_fin__gte=debut_mois
                )
                base = {
                    'nom': agent.personne.nom,
                    'prenom': agent.personne.prenom,
                    'poste': agent.poste,
                    'grade': agent.grade
                }
                if type_rapport == 'detaille':
                    total_jours = sum((abs.date_fin - max(abs.date_debut, debut_mois)).days + 1 for abs in absences)
                    donnees.append({
                        **base,
                        'nombre_absences': absences.count(),
                        'jours_absence': total_jours,
                        'types_absence': ', '.join(absences.values_list('type_absence', flat=True).distinct())
                    })
                else:
                    donnees.append({
                        **base,
                        'nombre_absences': absences.count(),
                        'jours_absence': sum((abs.date_fin - abs.date_debut).days + 1 for abs in absences)
                    })

            if format_export == 'csv':
                output = StringIO()
                if donnees:
                    writer = csv.DictWriter(output, fieldnames=donnees[0].keys())
                    writer.writeheader()
                    writer.writerows(donnees)
                resp = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
                resp['Content-Disposition'] = f'attachment; filename="rapport_pat_{type_rapport}_{mois}.csv"'
                return resp

            return Response({
                'donnees': donnees,
                'periode': mois,
                'service': service.nom,
                'type_rapport': type_rapport,
                'genere_le': timezone.now().isoformat()
            })
        except Service.DoesNotExist:
            return Response({'error': 'Service non trouvé'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


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
    @action(detail=False, methods=['get'])
    def planning_validation(self, request):
        """Planning des absences à valider pour les chefs"""
        user = request.user
        
        if not user.role.startswith('chef_') and user.role != 'admin_rh':
            return Response({'error': 'Permission refusée'}, status=403)
        
        try:
            # Déterminer le scope
            if user.role == 'admin_rh':
                absences = Absence.objects.filter(statut='EN_ATTENTE')
            else:
                service = Service.objects.get(chef_service=user)
                absences = Absence.objects.filter(
                    personne__service=service,
                    statut='EN_ATTENTE'
                )
            
            # Organiser par priorité
            aujourd_hui = timezone.now().date()
            
            # Absences urgentes (dans les 3 jours)
            absences_urgentes = absences.filter(
                date_debut__lte=aujourd_hui + timedelta(days=3)
            ).select_related('personne')
            
            # Absences cette semaine (4-7 jours)
            absences_semaine = absences.filter(
                date_debut__gt=aujourd_hui + timedelta(days=3),
                date_debut__lte=aujourd_hui + timedelta(days=7)
            ).select_related('personne')
            
            # Absences futures (plus de 7 jours)
            absences_futures = absences.filter(
                date_debut__gt=aujourd_hui + timedelta(days=7)
            ).select_related('personne')
            
            return Response({
                'absences_urgentes': AbsenceSerializer(absences_urgentes, many=True).data,
                'absences_semaine': AbsenceSerializer(absences_semaine, many=True).data,
                'absences_futures': AbsenceSerializer(absences_futures, many=True).data,
                'statistiques': {
                    'total_en_attente': absences.count(),
                    'urgentes': absences_urgentes.count(),
                    'cette_semaine': absences_semaine.count(),
                    'futures': absences_futures.count()
                }
            })
            
        except Service.DoesNotExist:
            return Response({'error': 'Service non trouvé'}, status=404)

    @action(detail=False, methods=['post'])
    def validation_en_lot(self, request):
        """Valider plusieurs absences en une fois"""
        user = request.user
        
        if not user.role.startswith('chef_') and user.role != 'admin_rh':
            return Response({'error': 'Permission refusée'}, status=403)
        
        absence_ids = request.data.get('absence_ids', [])
        action_type = request.data.get('action', 'approuver')  # approuver ou refuser
        commentaire = request.data.get('commentaire', '')
        
        if not absence_ids:
            return Response({'error': 'Aucune absence sélectionnée'}, status=400)
        
        try:
            # Récupérer les absences
            absences = Absence.objects.filter(id__in=absence_ids, statut='EN_ATTENTE')
            
            # Vérifier les permissions pour chaque absence
            if user.role != 'admin_rh':
                service = Service.objects.get(chef_service=user)
                absences = absences.filter(personne__service=service)
            
            resultats = {
                'traitees': 0,
                'erreurs': []
            }
            
            for absence in absences:
                try:
                    if action_type == 'approuver':
                        absence.statut = 'APPROUVÉ'
                        absence.commentaire_approbateur = commentaire
                    else:
                        absence.statut = 'REFUSÉ'
                        absence.motif_refus = commentaire
                    
                    absence.approuve_par = user
                    absence.save()
                    resultats['traitees'] += 1
                    
                except Exception as e:
                    resultats['erreurs'].append({
                        'absence_id': absence.id,
                        'erreur': str(e)
                    })
            
            return Response({
                'message': f'{resultats["traitees"]} absences {action_type}ées avec succès',
                'resultats': resultats
            })
            
        except Service.DoesNotExist:
            return Response({'error': 'Service non trouvé'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)



class PlanningViewSet(viewsets.ViewSet):
    """
    ViewSet pour la gestion du planning
    """
    permission_classes = [IsAdminRHOrChefService]
    
    @action(detail=False, methods=['get'])
    def vue_mensuelle(self, request):
        """Vue mensuelle du planning selon le rôle"""
        user = request.user
        mois = request.query_params.get('mois', timezone.now().strftime('%Y-%m'))
        
        try:
            # Déterminer le scope selon le rôle
            if user.role == 'admin_rh':
                personnes = Personne.objects.all()
                scope_name = "Tous les services"
            elif user.role.startswith('chef_'):
                service = Service.objects.get(chef_service=user)
                personnes = service.employes.all()
                scope_name = service.nom
            else:
                return Response({'error': 'Permission refusée'}, status=403)
            
            # Dates du mois
            debut_mois = datetime.strptime(f"{mois}-01", '%Y-%m-%d').date()
            _, last_day = monthrange(debut_mois.year, debut_mois.month)
            fin_mois = debut_mois.replace(day=last_day)
            
            # Récupérer les absences
            absences = Absence.objects.filter(
                personne__in=personnes,
                date_debut__lte=fin_mois,
                date_fin__gte=debut_mois,
                statut='APPROUVÉ'
            ).select_related('personne')
            
            # Créer le planning calendaire
            planning_data = self._generer_planning_calendaire(debut_mois, fin_mois, absences)
            
            # Statistiques
            jours_travailles = self._calculer_jours_travailles(debut_mois, fin_mois)
            taux_presence_moyen = self._calculer_taux_presence(personnes.count(), absences, jours_travailles)
            
            return Response({
                'mois': mois,
                'scope': scope_name,
                'planning': planning_data,
                'statistiques': {
                    'total_employes': personnes.count(),
                    'total_absences': absences.count(),
                    'jours_travailles': jours_travailles,
                    'taux_presence_moyen': taux_presence_moyen
                }
            })
            
        except Service.DoesNotExist:
            return Response({'error': 'Service non trouvé'}, status=404)
    
    @action(detail=False, methods=['get'])
    def vue_hebdomadaire(self, request):
        """Vue hebdomadaire du planning"""
        user = request.user
        semaine = request.query_params.get('semaine')  # Format: 2024-W15
        
        if not semaine:
            # Semaine courante
            today = timezone.now().date()
            year, week, _ = today.isocalendar()
            semaine = f"{year}-W{week:02d}"
        
        try:
            # Parser la semaine
            year, week_num = semaine.split('-W')
            year = int(year)
            week_num = int(week_num)
            
            # Calculer les dates de début et fin de semaine
            debut_semaine = datetime.strptime(f"{year}-W{week_num:02d}-1", "%Y-W%W-%w").date()
            fin_semaine = debut_semaine + timedelta(days=6)
            
            # Déterminer le scope
            if user.role == 'admin_rh':
                personnes = Personne.objects.all()
                scope_name = "Tous les services"
            elif user.role.startswith('chef_'):
                service = Service.objects.get(chef_service=user)
                personnes = service.employes.all()
                scope_name = service.nom
            else:
                return Response({'error': 'Permission refusée'}, status=403)
            
            # Récupérer les absences de la semaine
            absences = Absence.objects.filter(
                personne__in=personnes,
                date_debut__lte=fin_semaine,
                date_fin__gte=debut_semaine,
                statut='APPROUVÉ'
            ).select_related('personne')
            
            # Organiser par jour de la semaine
            planning_semaine = {}
            jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
            
            for i in range(7):
                jour_date = debut_semaine + timedelta(days=i)
                day_key = jour_date.strftime('%Y-%m-%d')
                
                planning_semaine[day_key] = {
                    'date': day_key,
                    'jour_semaine': jours[i],
                    'est_weekend': i >= 5,
                    'absents': []
                }
            
            # Remplir avec les absences
            for absence in absences:
                start_date = max(absence.date_debut, debut_semaine)
                end_date = min(absence.date_fin, fin_semaine)
                
                current = start_date
                while current <= end_date:
                    day_key = current.strftime('%Y-%m-%d')
                    if day_key in planning_semaine:
                        planning_semaine[day_key]['absents'].append({
                            'nom': f"{absence.personne.prenom} {absence.personne.nom}",
                            'type_absence': absence.type_absence,
                            'service': absence.personne.service.nom if absence.personne.service else 'N/A'
                        })
                    current += timedelta(days=1)
            
            return Response({
                'semaine': semaine,
                'debut_semaine': debut_semaine.isoformat(),
                'fin_semaine': fin_semaine.isoformat(),
                'scope': scope_name,
                'planning': planning_semaine
            })
            
        except (ValueError, Service.DoesNotExist) as e:
            return Response({'error': str(e)}, status=400)
    
    def _generer_planning_calendaire(self, debut, fin, absences):
        """Génère un planning calendaire"""
        planning = {}
        current_date = debut
        
        # Initialiser tous les jours
        while current_date <= fin:
            day_key = current_date.strftime('%Y-%m-%d')
            planning[day_key] = {
                'date': day_key,
                'jour_semaine': current_date.strftime('%A'),
                'numero_jour': current_date.day,
                'est_weekend': current_date.weekday() >= 5,
                'absents': [],
                'nombre_absents': 0
            }
            current_date += timedelta(days=1)
        
        # Remplir avec les absences
        for absence in absences:
            start_date = max(absence.date_debut, debut)
            end_date = min(absence.date_fin, fin)
            
            current = start_date
            while current <= end_date:
                day_key = current.strftime('%Y-%m-%d')
                if day_key in planning:
                    planning[day_key]['absents'].append({
                        'nom': f"{absence.personne.prenom} {absence.personne.nom}",
                        'type_absence': absence.type_absence,
                        'service': absence.personne.service.nom if absence.personne.service else 'N/A'
                    })
                current += timedelta(days=1)
        
        # Calculer le nombre d'absents par jour
        for day_data in planning.values():
            day_data['nombre_absents'] = len(day_data['absents'])
        
        return planning
    
    def _calculer_jours_travailles(self, debut, fin):
        """Calcule le nombre de jours ouvrables"""
        jours = 0
        current = debut
        while current <= fin:
            if current.weekday() < 5:  # Lundi à Vendredi
                jours += 1
            current += timedelta(days=1)
        return jours
    
    def _calculer_taux_presence(self, nb_employes, absences, jours_travailles):
        """Calcule le taux de présence moyen"""
        if nb_employes == 0 or jours_travailles == 0:
            return 100
        
        total_jours_employes = nb_employes * jours_travailles
        total_jours_absences = sum((min(abs.date_fin, timezone.now().date()) - abs.date_debut).days + 1 for abs in absences)
        
        taux = ((total_jours_employes - total_jours_absences) / total_jours_employes) * 100
        return round(max(0, taux), 2)
    
class StatistiquesViewSet(viewsets.ViewSet):
    """
    ViewSet pour les statistiques avancées
    """
    permission_classes = [IsAdminRHOrChefService]
    
    @action(detail=False, methods=['get'])
    def tableau_bord_chef(self, request):
        """Tableau de bord spécialisé pour chef de service"""
        user = request.user
        
        if not user.role.startswith('chef_'):
            return Response({'error': 'Permission refusée'}, status=403)
        
        try:
            service = Service.objects.get(chef_service=user)
            
            # Période par défaut : 3 derniers mois
            aujourd_hui = timezone.now().date()
            debut_periode = aujourd_hui.replace(day=1) - timedelta(days=90)
            
            # Employés du service
            employes = service.employes.all()
            total_employes = employes.count()
            
            # Absences récentes
            absences_recentes = Absence.objects.filter(
                personne__service=service,
                date_debut__gte=debut_periode
            )
            
            # Statistiques des absences
            absences_par_mois = []
            for i in range(3):
                date_mois = aujourd_hui.replace(day=1) - timedelta(days=30*i)
                debut_mois = date_mois.replace(day=1)
                _, last_day = monthrange(date_mois.year, date_mois.month)
                fin_mois = date_mois.replace(day=last_day)
                
                nb_absences = Absence.objects.filter(
                    personne__service=service,
                    date_debut__lte=fin_mois,
                    date_fin__gte=debut_mois
                ).count()
                
                absences_par_mois.append({
                    'mois': date_mois.strftime('%Y-%m'),
                    'nom_mois': date_mois.strftime('%B %Y'),
                    'nombre_absences': nb_absences
                })
            
            # Top 5 employés par absences
            top_absences = []
            for employe in employes:
                nb_absences = Absence.objects.filter(
                    personne=employe,
                    date_debut__gte=debut_periode
                ).count()
                
                if nb_absences > 0:
                    top_absences.append({
                        'nom': f"{employe.prenom} {employe.nom}",
                        'fonction': employe.fonction,
                        'nombre_absences': nb_absences
                    })
            
            top_absences.sort(key=lambda x: x['nombre_absences'], reverse=True)
            top_absences = top_absences[:5]
            
            # Absences en attente de validation
            absences_attente = Absence.objects.filter(
                personne__service=service,
                statut='EN_ATTENTE'
            ).count()
            
            # Répartition par type d'employé
            if service.type_service == 'enseignant':
                repartition = employes.filter(type_employe='enseignant').values(
                    'enseignant__grade'
                ).annotate(count=Count('id'))
            elif service.type_service == 'pat':
                repartition = employes.filter(type_employe='pat').values(
                    'personnelpat__poste'
                ).annotate(count=Count('id'))
            else:
                repartition = employes.filter(type_employe='contractuel').values(
                    'contractuel__type_contrat'
                ).annotate(count=Count('id'))
            
            return Response({
                'service': {
                    'nom': service.nom,
                    'type': service.type_service,
                    'chef': user.get_full_name()
                },
                'statistiques_generales': {
                    'total_employes': total_employes,
                    'absences_attente': absences_attente,
                    'periode_analyse': f"{debut_periode} - {aujourd_hui}"
                },
                'absences_par_mois': absences_par_mois,
                'top_absences': top_absences,
                'repartition_employes': list(repartition),
                'genere_le': timezone.now().isoformat()
            })
            
        except Service.DoesNotExist:
            return Response({'error': 'Service non trouvé'}, status=404)
    
    @action(detail=False, methods=['get'])
    def comparaison_periodes(self, request):
        """Compare les statistiques entre deux périodes"""
        user = request.user
        
        if not user.role.startswith('chef_') and user.role != 'admin_rh':
            return Response({'error': 'Permission refusée'}, status=403)
        
        # Paramètres
        periode1_debut = request.query_params.get('periode1_debut')
        periode1_fin = request.query_params.get('periode1_fin')
        periode2_debut = request.query_params.get('periode2_debut')
        periode2_fin = request.query_params.get('periode2_fin')
        
        if not all([periode1_debut, periode1_fin, periode2_debut, periode2_fin]):
            return Response({'error': 'Toutes les dates de période sont requises'}, status=400)
        
        try:
            # Convertir les dates
            p1_debut = datetime.strptime(periode1_debut, '%Y-%m-%d').date()
            p1_fin = datetime.strptime(periode1_fin, '%Y-%m-%d').date()
            p2_debut = datetime.strptime(periode2_debut, '%Y-%m-%d').date()
            p2_fin = datetime.strptime(periode2_fin, '%Y-%m-%d').date()
            
            # Déterminer le scope
            if user.role == 'admin_rh':
                employes = Personne.objects.all()
                scope_name = "Tous les services"
            else:
                service = Service.objects.get(chef_service=user)
                employes = service.employes.all()
                scope_name = service.nom
            
            # Statistiques période 1
            absences_p1 = Absence.objects.filter(
                personne__in=employes,
                date_debut__lte=p1_fin,
                date_fin__gte=p1_debut
            )
            
            stats_p1 = {
                'nombre_absences': absences_p1.count(),
                'jours_absence': sum((abs.date_fin - abs.date_debut).days + 1 for abs in absences_p1),
                'types_absence': dict(absences_p1.values('type_absence').annotate(count=Count('id')).values_list('type_absence', 'count'))
            }
            
            # Statistiques période 2
            absences_p2 = Absence.objects.filter(
                personne__in=employes,
                date_debut__lte=p2_fin,
                date_fin__gte=p2_debut
            )
            
            stats_p2 = {
                'nombre_absences': absences_p2.count(),
                'jours_absence': sum((abs.date_fin - abs.date_debut).days + 1 for abs in absences_p2),
                'types_absence': dict(absences_p2.values('type_absence').annotate(count=Count('id')).values_list('type_absence', 'count'))
            }
            
            # Calculs des évolutions
            evolution_absences = ((stats_p2['nombre_absences'] - stats_p1['nombre_absences']) / 
                                max(stats_p1['nombre_absences'], 1)) * 100
            
            evolution_jours = ((stats_p2['jours_absence'] - stats_p1['jours_absence']) / 
                             max(stats_p1['jours_absence'], 1)) * 100
            
            return Response({
                'scope': scope_name,
                'periode1': {
                    'debut': periode1_debut,
                    'fin': periode1_fin,
                    'statistiques': stats_p1
                },
                'periode2': {
                    'debut': periode2_debut,
                    'fin': periode2_fin,
                    'statistiques': stats_p2
                },
                'evolutions': {
                    'nombre_absences': round(evolution_absences, 2),
                    'jours_absence': round(evolution_jours, 2)
                }
            })
            
        except (ValueError, Service.DoesNotExist) as e:
            return Response({'error': str(e)}, status=400)
        
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