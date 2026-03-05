from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import (
    User, Service, Structure, Personne, Enseignant, PersonnelPAT, Contractuel,
    Recrutement, Candidat, Absence, Paie, ElementPaie, Detachement, Document,
    StatutOffre, TypeStructure,  TypeContrat, TypeAbsence,
    StatutPaiement, StatutAbsence, TypeDocument, StatutCandidature
)


# ========================================
# NOUVEAUX SERIALIZERS HIÉRARCHIQUES
# ========================================

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    service_info = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'role', 
            'is_active', 'date_joined', 'password', 'confirm_password',
            'full_name', 'service_info', 'phone'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'confirm_password': {'write_only': True}
        }
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username
    
    def get_service_info(self, obj):
        """Retourne les infos du service selon le rôle"""
        if obj.role.startswith('chef_'):
            try:
                service = Service.objects.get(chef_service=obj)
                return {
                    'id': service.id,
                    'nom': service.nom,
                    'type_service': service.type_service
                }
            except Service.DoesNotExist:
                return None
        elif hasattr(obj, 'personne') and obj.personne.service:
            service = obj.personne.service
            return {
                'id': service.id,
                'nom': service.nom,
                'type_service': service.type_service
            }
        return None
    
    def validate(self, attrs):
        if attrs.get('password') != attrs.get('confirm_password'):
            raise serializers.ValidationError("Les mots de passe ne correspondent pas")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        validated_data.pop('confirm_password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class ServiceSerializer(serializers.ModelSerializer):
    chef_service_name = serializers.CharField(source='chef_service.get_full_name', read_only=True)
    chef_service_email = serializers.CharField(source='chef_service.email', read_only=True)
    nombre_employes = serializers.SerializerMethodField()
    repartition_employes = serializers.SerializerMethodField()
    
    class Meta:
        model = Service
        fields = [
            'id', 'nom', 'type_service', 'chef_service', 'chef_service_name', 
            'chef_service_email', 'description', 'created_at', 'nombre_employes',
            'repartition_employes'
        ]
    
    def get_nombre_employes(self, obj):
        return obj.employes.count()
    
    def get_repartition_employes(self, obj):
        """Répartition des employés par type"""
        employes = obj.employes.all()
        return {
            'enseignant': employes.filter(type_employe='enseignant').count(),
            'pat': employes.filter(type_employe='pat').count(),
            'contractuel': employes.filter(type_employe='contractuel').count(),
        }
    
    def validate_chef_service(self, value):
        """Valider que le chef a le bon rôle"""
        if value and not value.role.startswith('chef_'):
            raise serializers.ValidationError("L'utilisateur doit avoir un rôle de chef de service")
        return value


class PersonneSerializer(serializers.ModelSerializer):
    manager_nom = serializers.CharField(source='manager.nom', read_only=True)
    manager_prenom = serializers.CharField(source='manager.prenom', read_only=True)
    service_nom = serializers.CharField(source='service.nom', read_only=True)
    service_type = serializers.CharField(source='service.type_service', read_only=True)
    chef_service_nom = serializers.CharField(source='service.chef_service.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    age = serializers.SerializerMethodField()
    nom_complet = serializers.SerializerMethodField()
    
    class Meta:
        model = Personne
        fields = [
            'id', 'user', 'nom', 'prenom', 'nom_complet', 'date_naissance', 'age',
            'lieu_naissance', 'nni', 'nationalite', 'genre', 'situation_familiale',
            'adresse', 'nom_pere', 'dernier_diplome', 'pays_obtention_diplome',
            'annee_obtention_diplome', 'specialite_formation', 'fonction',
            'type_employe', 'numero_employe', 'date_embauche', 'service',
            'service_nom', 'service_type', 'chef_service_nom', 'structure',
            'manager', 'manager_nom', 'manager_prenom', 'statut_actif',
            'user_email', 'user_username', 'created_at', 'updated_at'
        ]
    
    def get_age(self, obj):
        from datetime import date
        today = date.today()
        return today.year - obj.date_naissance.year - ((today.month, today.day) < (obj.date_naissance.month, obj.date_naissance.day))
    
    def get_nom_complet(self, obj):
        return f"{obj.prenom} {obj.nom}"
    
    def validate_nni(self, value):
        """Valider le format NNI (10 chiffres)"""
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Le NNI doit contenir exactement 10 chiffres")
        return value
    
    def validate_numero_employe(self, value):
        """Valider l'unicité du numéro employé"""
        if self.instance and self.instance.numero_employe == value:
            return value
        
        if Personne.objects.filter(numero_employe=value).exists():
            raise serializers.ValidationError("Ce numéro d'employé existe déjà")
        return value
    
    def validate(self, attrs):
        """Validation globale"""
        # Vérifier cohérence type_employe et service
        service = attrs.get('service') or (self.instance.service if self.instance else None)
        type_employe = attrs.get('type_employe') or (self.instance.type_employe if self.instance else None)
        
        if service and type_employe:
            if service.type_service != type_employe:
                raise serializers.ValidationError(
                    f"Le type d'employé '{type_employe}' ne correspond pas au service '{service.type_service}'"
                )
        
        return attrs


class EnseignantSerializer(serializers.ModelSerializer):
    personne = PersonneSerializer(read_only=True)
    personne_id = serializers.IntegerField(write_only=True)
    personne_nom_complet = serializers.CharField(source='personne.prenom', read_only=True)
    personne_service = serializers.CharField(source='personne.service.nom', read_only=True)
    anciennete_service = serializers.SerializerMethodField()
    
    class Meta:
        model = Enseignant
        fields = [
            'personne', 'personne_id', 'personne_nom_complet', 'personne_service',
            'corps', 'grade', 'echelon', 'indice', 'date_entree_service_publique', 
            'date_entree_enseignement_superieur', 'date_fin_service_obligatoire',
            'anciennete_service'
        ]
    
    def get_anciennete_service(self, obj):
        """Calcul de l'ancienneté en années"""
        from datetime import date
        today = date.today()
        return today.year - obj.date_entree_enseignement_superieur.year
    
    def validate_personne_id(self, value):
        """Valider que la personne existe et est du bon type"""
        try:
            personne = Personne.objects.get(id=value)
            if personne.type_employe != 'enseignant':
                raise serializers.ValidationError("Cette personne n'est pas de type enseignant")
            return value
        except Personne.DoesNotExist:
            raise serializers.ValidationError("Personne non trouvée")


class PersonnelPATSerializer(serializers.ModelSerializer):
    personne = PersonneSerializer(read_only=True)
    personne_id = serializers.IntegerField(write_only=True, required=False)
    
    # ✅ Ajouter TOUS les champs nécessaires pour le frontend
    personne_nom_complet = serializers.SerializerMethodField()
    personne_nom = serializers.CharField(source='personne.nom', read_only=True)
    personne_prenom = serializers.CharField(source='personne.prenom', read_only=True)
    personne_service = serializers.CharField(source='personne.service.nom', read_only=True)
    personne_fonction = serializers.CharField(source='personne.fonction', read_only=True)
    
    poste_label = serializers.SerializerMethodField()
    anciennete_grade_annees = serializers.SerializerMethodField()
    
    # ✅ IMPORTANT: Ajouter l'ID pour les clés uniques dans le frontend
    id = serializers.IntegerField(source='personne.id', read_only=True)
    
    class Meta:
        model = PersonnelPAT
        fields = [
            'id',  # ✅ CRUCIAL pour React keys
            'personne', 'personne_id', 
            'personne_nom', 'personne_prenom', 'personne_nom_complet',  # ✅ AJOUTÉS
            'personne_service', 'personne_fonction',  # ✅ AJOUTÉ
            'grade', 'poste', 'poste_label',
            'nbi_mac', 'indice', 'anciennete_echelon',
            'date_changement', 'anciennete_grade', 'date_nomination',
            'date_prise_service', 'anciennete_grade_annees'
        ]
    
    def get_personne_nom_complet(self, obj):
        if obj.personne:
            return f"{obj.personne.prenom} {obj.personne.nom}"
        return "N/A"
    
    def get_poste_label(self, obj):
        return dict(PersonnelPAT.POSTE_CHOICES).get(obj.poste, obj.poste)
    
    def get_anciennete_grade_annees(self, obj):
        from datetime import date
        today = date.today()
        return today.year - obj.date_nomination.year if obj.date_nomination else 0
    
    def validate_personne_id(self, value):
        try:
            personne = Personne.objects.get(id=value)
            if personne.type_employe != 'pat':
                raise serializers.ValidationError("Cette personne n'est pas de type PAT")
            return value
        except Personne.DoesNotExist:
            raise serializers.ValidationError("Personne non trouvée")
    
    def update(self, instance, validated_data):
        """Mise à jour du PersonnelPAT avec gestion des données Personne imbriquées"""
        # Extraire les données personne si présentes dans la requête initiale
        request = self.context.get('request')
        if request and hasattr(request, 'data'):
            personne_data = request.data.get('personne', {})
            if personne_data and instance.personne:
                # Mettre à jour les champs de Personne
                personne = instance.personne
                for attr, value in personne_data.items():
                    if hasattr(personne, attr) and value is not None:
                        setattr(personne, attr, value)
                personne.save()
        
        # Mettre à jour les champs PAT
        for attr, value in validated_data.items():
            if attr != 'personne_id':
                setattr(instance, attr, value)
        instance.save()
        
        return instance

class ContractuelSerializer(serializers.ModelSerializer):
    personne = PersonneSerializer(read_only=True)
    personne_id = serializers.IntegerField(write_only=True)
    personne_nom_complet = serializers.CharField(source='personne.prenom', read_only=True)
    personne_service = serializers.CharField(source='personne.service.nom', read_only=True)
    duree_contrat_jours = serializers.SerializerMethodField()
    jours_restants = serializers.SerializerMethodField()
    
    class Meta:
        model = Contractuel
        fields = [
            'personne', 'personne_id', 'personne_nom_complet', 'personne_service',
            'type_contrat', 'duree_contrat', 'date_debut_contrat', 'date_fin_contrat',
            'salaire_mensuel', 'duree_contrat_jours', 'jours_restants'
        ]
    
    def get_duree_contrat_jours(self, obj):
        """Durée totale du contrat en jours"""
        if obj.date_fin_contrat:
            return (obj.date_fin_contrat - obj.date_debut_contrat).days
        return None
    
    def get_jours_restants(self, obj):
        """Jours restants avant fin de contrat"""
        if obj.date_fin_contrat:
            from datetime import date
            today = date.today()
            if obj.date_fin_contrat > today:
                return (obj.date_fin_contrat - today).days
            return 0
        return None
    
    def validate_personne_id(self, value):
        try:
            personne = Personne.objects.get(id=value)
            if personne.type_employe != 'contractuel':
                raise serializers.ValidationError("Cette personne n'est pas de type contractuel")
            return value
        except Personne.DoesNotExist:
            raise serializers.ValidationError("Personne non trouvée")
    
    def validate(self, attrs):
        date_debut = attrs.get('date_debut_contrat')
        date_fin = attrs.get('date_fin_contrat')
        
        if date_fin and date_debut and date_fin <= date_debut:
            raise serializers.ValidationError("La date de fin doit être postérieure à la date de début")
        
        return attrs


# ========================================
# SERIALIZERS EXISTANTS ADAPTÉS
# ========================================

class StructureSerializer(serializers.ModelSerializer):
    responsable_nom = serializers.CharField(source='responsable.nom', read_only=True)
    responsable_prenom = serializers.CharField(source='responsable.prenom', read_only=True)
    parent_structure_nom = serializers.CharField(source='parent_structure.nom', read_only=True)
    service_nom = serializers.CharField(source='service.nom', read_only=True)
    nombre_employes = serializers.SerializerMethodField()
    
    class Meta:
        model = Structure
        fields = [
            'id', 'nom', 'responsable', 'responsable_nom', 'responsable_prenom',
            'type_structure', 'description', 'parent_structure', 'parent_structure_nom',
            'service', 'service_nom', 'nombre_employes'
        ]
    
    def get_nombre_employes(self, obj):
        return obj.employes.count() if hasattr(obj, 'employes') else 0


class RecrutementSerializer(serializers.ModelSerializer):
    structure_recruteur_nom = serializers.CharField(source='structure_recruteur.nom', read_only=True)
    service_recruteur_nom = serializers.CharField(source='service_recruteur.nom', read_only=True)
    nombre_candidats = serializers.SerializerMethodField()
    
    class Meta:
        model = Recrutement
        fields = [
            'id', 'titre_poste', 'type_employe', 'type_employe_specifique',
            'description', 'requis_post', 'date_publication', 'date_limite',
            'date_entree_prevue', 'statut_offre', 'service_recruteur',
            'service_recruteur_nom', 'structure_recruteur', 'structure_recruteur_nom',
            'nombre_postes', 'nombre_candidats'
        ]
    
    def get_nombre_candidats(self, obj):
        return obj.candidats.count()


class CandidatSerializer(serializers.ModelSerializer):
    recrutement_titre = serializers.CharField(source='recrutement.titre_poste', read_only=True)
    nom_complet = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidat
        fields = [
            'id', 'nom', 'prenom', 'nom_complet', 'email', 'telephone',
            'date_candidature', 'cv', 'lettre_motivation', 'statut_candidature',
            'recrutement', 'recrutement_titre', 'notes_evaluation', 'date_entretien'
        ]
    
    def get_nom_complet(self, obj):
        return f"{obj.prenom} {obj.nom}"


class AbsenceSerializer(serializers.ModelSerializer):
    personne_nom = serializers.CharField(source='personne.nom', read_only=True)
    personne_prenom = serializers.CharField(source='personne.prenom', read_only=True)
    personne_service = serializers.CharField(source='personne.service.nom', read_only=True)
    approuve_par_nom = serializers.CharField(source='approuve_par.get_full_name', read_only=True)
    duree_absence = serializers.SerializerMethodField()
    peut_approuver = serializers.SerializerMethodField()
    personne = serializers.PrimaryKeyRelatedField(
        queryset=Personne.objects.all(),
        required=False,  # Rendre optionnel pour permettre aux employés de ne pas le fournir
        allow_null=True
    )
    
    class Meta:
        model = Absence
        fields = [
            'id', 'personne', 'personne_nom', 'personne_prenom', 'personne_service',
            'type_absence', 'date_debut', 'date_fin', 'duree_absence', 'statut',
            'motif', 'document_justificatif', 'date_demande_absence', 'motif_refus',
            'approuve_par', 'approuve_par_nom', 'commentaire_approbateur',
            'peut_approuver'
        ]
    
    def get_duree_absence(self, obj):
        return (obj.date_fin - obj.date_debut).days + 1
    
    def get_peut_approuver(self, obj):
        """Indique si l'utilisateur connecté peut approuver cette absence"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.peut_approuver(request.user)
        return False


class ElementPaieSerializer(serializers.ModelSerializer):
    """Serializer pour les éléments détaillés du bulletin"""
    class Meta:
        model = ElementPaie
        fields = [
            'id', 'code', 'libelle', 'type_element', 'taux', 'montant',
            'date_debut', 'date_fin', 'ordre'
        ]


class PaieSerializer(serializers.ModelSerializer):
    personne_nom = serializers.CharField(source='personne.nom', read_only=True)
    personne_prenom = serializers.CharField(source='personne.prenom', read_only=True)
    personne_service = serializers.CharField(source='personne.service.nom', read_only=True)
    personne_nni = serializers.CharField(source='personne.nni', read_only=True)
    personne_genre = serializers.CharField(source='personne.genre', read_only=True)
    personne_numero_employe = serializers.CharField(source='personne.numero_employe', read_only=True)
    traite_par_nom = serializers.CharField(source='traite_par.get_full_name', read_only=True)
    elements = ElementPaieSerializer(many=True, read_only=True)
    
    class Meta:
        model = Paie
        fields = [
            'id', 'personne', 'personne_nom', 'personne_prenom', 'personne_service', 'personne_nni',
            'personne_genre', 'personne_numero_employe', 'salaire_net', 'salaire_brut', 'nb_enfants', 
            'allocations_familiales', 'deductions', 'date_paiement', 'mois_annee', 'statut_paiement',
            'traite_par', 'traite_par_nom', 'grade', 'echelon', 'indice',
            'mode_reglement', 'compte_bancaire', 'montant_imposable_mensuel',
            'montant_imposable_progressif', 'elements'
        ]


class DetachementSerializer(serializers.ModelSerializer):
    personne_nom = serializers.CharField(source='personne.nom', read_only=True)
    personne_prenom = serializers.CharField(source='personne.prenom', read_only=True)
    structure_origine_nom = serializers.CharField(source='structure_origine.nom', read_only=True)
    structure_detachement_nom = serializers.CharField(source='structure_detachement.nom', read_only=True)
    duree_detachement = serializers.SerializerMethodField()
    
    class Meta:
        model = Detachement
        fields = [
            'id', 'personne', 'personne_nom', 'personne_prenom',
            'acte_detachement', 'date_debut_detachement', 'date_fin_detachement',
            'structure_origine', 'structure_origine_nom', 'structure_detachement',
            'structure_detachement_nom', 'motif_detachement', 'statut',
            'duree_detachement'
        ]
    
    def get_duree_detachement(self, obj):
        return (obj.date_fin_detachement - obj.date_debut_detachement).days


class DocumentSerializer(serializers.ModelSerializer):
    proprietaire_nom = serializers.CharField(source='proprietaire.nom', read_only=True)
    proprietaire_prenom = serializers.CharField(source='proprietaire.prenom', read_only=True)
    uploade_par_nom = serializers.CharField(source='uploade_par.get_full_name', read_only=True)
    taille_fichier_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'nom', 'type_document', 'chemin_fichier', 'taille_fichier',
            'taille_fichier_mb', 'date_upload', 'proprietaire', 'proprietaire_nom',
            'proprietaire_prenom', 'uploade_par', 'uploade_par_nom'
        ]
        extra_kwargs = {
            'nom': {'required': False},
            'chemin_fichier': {'required': False},
            'taille_fichier': {'required': False},
            'proprietaire': {'required': False},
        }
    
    def get_taille_fichier_mb(self, obj):
        """Taille en MB pour affichage"""
        if obj.taille_fichier:
            return round(obj.taille_fichier / (1024 * 1024), 2)
        return 0
    
    def to_internal_value(self, data):
        """Intercepter les données avant validation pour gérer les alias"""
        request = self.context.get('request')
        
        # Créer une copie mutable des données
        if hasattr(data, '_mutable'):
            data._mutable = True
        
        # Si 'nom' n'est pas présent mais 'titre' l'est, utiliser 'titre'
        if request and hasattr(request, 'data'):
            if 'nom' not in request.data and 'titre' in request.data:
                if not hasattr(data, 'get') or data.get('nom') is None:
                    # Ajouter 'nom' avec la valeur de 'titre'
                    if isinstance(data, dict):
                        data['nom'] = request.data['titre']
                    elif hasattr(data, 'append'):
                        # Pour QueryDict, utiliser update
                        pass
        
        # Pour les fichiers, DRF les gère automatiquement depuis request.FILES
        # Pas besoin de les modifier ici
        
        return super().to_internal_value(data)
    
    def validate(self, attrs):
        """Validation personnalisée pour gérer les champs du frontend"""
        request = self.context.get('request')
        errors = {}
        
        # Récupérer 'nom' depuis attrs ou request.data (support 'titre' comme alias)
        if 'nom' not in attrs or not attrs.get('nom'):
            if request and hasattr(request, 'data'):
                if 'nom' in request.data:
                    attrs['nom'] = request.data['nom']
                elif 'titre' in request.data:
                    attrs['nom'] = request.data['titre']
        
        # Récupérer 'chemin_fichier' depuis attrs, request.FILES ou request.data (support 'fichier' comme alias)
        if 'chemin_fichier' not in attrs or not attrs.get('chemin_fichier'):
            fichier_trouve = None
            
            # Chercher dans request.FILES d'abord
            if request and hasattr(request, 'FILES') and request.FILES:
                if 'chemin_fichier' in request.FILES:
                    fichier_trouve = request.FILES['chemin_fichier']
                elif 'fichier' in request.FILES:
                    fichier_trouve = request.FILES['fichier']
            
            # Si pas trouvé dans FILES, chercher dans request.data (cas où le fichier serait mal parsé)
            if not fichier_trouve and request and hasattr(request, 'data'):
                if 'chemin_fichier' in request.data:
                    valeur = request.data['chemin_fichier']
                    # Vérifier si c'est un fichier uploadé
                    if hasattr(valeur, 'read') or (hasattr(valeur, 'file') and hasattr(valeur.file, 'read')):
                        fichier_trouve = valeur
                elif 'fichier' in request.data:
                    valeur = request.data['fichier']
                    if hasattr(valeur, 'read') or (hasattr(valeur, 'file') and hasattr(valeur.file, 'read')):
                        fichier_trouve = valeur
            
            if fichier_trouve:
                attrs['chemin_fichier'] = fichier_trouve
        
        # Calculer taille_fichier si chemin_fichier est présent
        if 'chemin_fichier' in attrs and attrs['chemin_fichier']:
            attrs['taille_fichier'] = attrs['chemin_fichier'].size
        
        # Validation des champs requis avec messages d'erreur détaillés
        if not attrs.get('nom'):
            errors['nom'] = 'Le titre est requis'
        
        if not attrs.get('chemin_fichier'):
            errors['chemin_fichier'] = 'Le fichier est requis'
        
        if not attrs.get('type_document'):
            errors['type_document'] = 'Le type de document est requis'
        else:
            # Vérifier que le type_document est valide
            valid_types = [choice[0] for choice in Document.TYPE_DOCUMENT_CHOICES]
            if attrs.get('type_document') not in valid_types:
                errors['type_document'] = f'Type de document invalide. Types acceptés: {", ".join(valid_types)}'
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return attrs
    
    def create(self, validated_data):
        """Gérer la création avec attribution automatique pour les employés"""
        request = self.context.get('request')
        
        # Si proprietaire n'est pas fourni et que c'est un employé, le récupérer automatiquement
        if 'proprietaire' not in validated_data:
            user = request.user if request else None
            if user and user.role == 'employe':
                try:
                    personne = Personne.objects.get(user=user)
                    validated_data['proprietaire'] = personne
                except Personne.DoesNotExist:
                    raise serializers.ValidationError({'proprietaire': 'Vous devez d\'abord compléter votre profil'})
        
        # Définir uploade_par si non fourni
        if 'uploade_par' not in validated_data and request:
            validated_data['uploade_par'] = request.user
        
        return super().create(validated_data)


# ========================================
# SERIALIZERS DÉTAILLÉS
# ========================================

class PersonneDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur détaillé pour une personne avec toutes ses relations"""
    absences = AbsenceSerializer(many=True, read_only=True)
    paies = PaieSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    detachements = DetachementSerializer(many=True, read_only=True)
    equipe = PersonneSerializer(many=True, read_only=True)
    service_info = serializers.SerializerMethodField()
    type_employe_details = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    user_username = serializers.SerializerMethodField()
    nom_complet = serializers.SerializerMethodField()
    
    class Meta:
        model = Personne
        fields = '__all__'
    
    def get_service_info(self, obj):
        if obj.service:
            return {
                'id': obj.service.id,
                'nom': obj.service.nom,
                'type_service': obj.service.type_service,
                'chef_service': obj.service.chef_service.get_full_name() if obj.service.chef_service else None
            }
        return None
    
    def get_type_employe_details(self, obj):
        """Retourne les détails spécifiques selon le type d'employé"""
        if obj.type_employe == 'enseignant':
            try:
                enseignant = obj.enseignant
                return EnseignantSerializer(enseignant).data
            except:
                return None
        elif obj.type_employe == 'pat':
            try:
                pat = obj.personnelpat
                return PersonnelPATSerializer(pat).data
            except:
                return None
        elif obj.type_employe == 'contractuel':
            try:
                contractuel = obj.contractuel
                return ContractuelSerializer(contractuel).data
            except:
                return None
        return None
    
    def get_user_email(self, obj):
        """Retourne l'email de l'utilisateur"""
        if obj.user:
            return obj.user.email
        return None
    
    def get_user_username(self, obj):
        """Retourne le username de l'utilisateur"""
        if obj.user:
            return obj.user.username
        return None
    
    def get_nom_complet(self, obj):
        """Retourne le nom complet"""
        return f"{obj.prenom} {obj.nom}"


class StructureTreeSerializer(serializers.ModelSerializer):
    """Sérialiseur pour l'arborescence des structures"""
    sous_structures = serializers.SerializerMethodField()
    service_nom = serializers.CharField(source='service.nom', read_only=True)
    
    class Meta:
        model = Structure
        fields = [
            'id', 'nom', 'type_structure', 'description', 'service',
            'service_nom', 'sous_structures'
        ]
    
    def get_sous_structures(self, obj):
        if obj.sous_structures.exists():
            return StructureTreeSerializer(obj.sous_structures.all(), many=True).data
        return []


# ========================================
# SERIALIZERS D'ÉNUMÉRATION
# ========================================

class StatutOffreSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatutOffre
        fields = '__all__'

class TypeStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeStructure
        fields = '__all__'


class TypeContratSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeContrat
        fields = '__all__'

class TypeAbsenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeAbsence
        fields = '__all__'

class StatutPaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatutPaiement
        fields = '__all__'

class StatutAbsenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatutAbsence
        fields = '__all__'

class TypeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeDocument
        fields = '__all__'

class StatutCandidatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatutCandidature
        fields = '__all__'