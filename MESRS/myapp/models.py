from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """Modèle d'utilisateur étendu avec rôles hiérarchiques"""
    ROLE_CHOICES = [
        ('admin_rh', 'Administrateur RH'),
        ('chef_enseignant', 'Chef Service Enseignant'),
        ('chef_pat', 'Chef Service Personnel PAT'),
        ('chef_contractuel', 'Chef Service Contractuel'),
        ('employe', 'Employé'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employe')
    phone = models.CharField(max_length=15, blank=True)


class Service(models.Model):
    """Modèle pour les services avec chef de service"""
    SERVICE_TYPES = [
        ('enseignant', 'Service Enseignant'),
        ('pat', 'Service Personnel PAT'),
        ('contractuel', 'Service Contractuel'),
    ]
    nom = models.CharField(max_length=100)
    type_service = models.CharField(max_length=15, choices=SERVICE_TYPES)
    chef_service = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   limit_choices_to={'role__startswith': 'chef_'})
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nom


class Structure(models.Model):
    """Modèle pour les structures organisationnelles"""
    nom = models.CharField(max_length=255)
    responsable = models.ForeignKey('Personne', on_delete=models.SET_NULL, null=True, blank=True, related_name='structures_dirigees')
    type_structure = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent_structure = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sous_structures')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='structures')
    
    def __str__(self):
        return self.nom


class Personne(models.Model):
    """Modèle de base pour toutes les personnes du système"""
    GENRE_CHOICES = [
        ('MASCULIN', 'Masculin'),
        ('FEMININ', 'Féminin'),
    ]
    
    TYPE_EMPLOYE_CHOICES = [
        ('enseignant', 'Personnel Enseignant'),
        ('pat', 'Personnel PAT'),
        ('contractuel', 'Personnel Contractuel'),
    ]
    
    # Lien avec l'utilisateur Django
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Informations personnelles
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    date_naissance = models.DateField()
    lieu_naissance = models.CharField(max_length=100)
    nni = models.CharField(max_length=10, unique=True)  # 10 digits
    nationalite = models.CharField(max_length=100)
    genre = models.CharField(max_length=10, choices=GENRE_CHOICES)
    situation_familiale = models.CharField(max_length=50)
    adresse = models.TextField()
    nom_pere = models.CharField(max_length=100)
    
    # Formation
    dernier_diplome = models.CharField(max_length=200)
    pays_obtention_diplome = models.CharField(max_length=100)
    annee_obtention_diplome = models.IntegerField()
    specialite_formation = models.CharField(max_length=200)
    
    # Informations professionnelles
    fonction = models.CharField(max_length=100)
    type_employe = models.CharField(max_length=15, choices=TYPE_EMPLOYE_CHOICES)
    numero_employe = models.CharField(max_length=20, unique=True)
    date_embauche = models.DateField()
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='employes')
    structure = models.ForeignKey(Structure, on_delete=models.CASCADE, null=True, blank=True)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='equipe')
    
    # Statut
    statut_actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.prenom} {self.nom}"
    
    def get_chef_service(self):
        """Retourne le chef de service de cette personne"""
        return self.service.chef_service if self.service else None


class Enseignant(models.Model):
    """Modèle pour les enseignants"""
    GRADE_CHOICES = [
        ('professeur', 'Professeur'),
        ('maitre_assistant', 'Maître Assistant'),
        ('assistant', 'Assistant'),
        ('docteur', 'Docteur'),
    ]
    
    personne = models.OneToOneField(Personne, on_delete=models.CASCADE, primary_key=True)
    corps = models.CharField(max_length=100)
    grade = models.CharField(max_length=100, choices=GRADE_CHOICES)
    echelon = models.CharField(max_length=50)
    indice = models.IntegerField()
    date_entree_service_publique = models.DateField()
    date_entree_enseignement_superieur = models.DateField()
    date_fin_service_obligatoire = models.DateField()
    
    def save(self, *args, **kwargs):
        # S'assurer que le type_employe est bien 'enseignant'
        if self.personne:
            self.personne.type_employe = 'enseignant'
            self.personne.save()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Enseignant: {self.personne}"


class PersonnelPAT(models.Model):
    """Modèle pour le Personnel Administratif et Technique"""
    POSTE_CHOICES = [
        ('sg', 'Secrétaire Général'),
        ('conseil', 'Conseil'),
        ('charge_mission', 'Chargé de Mission'),
        ('directeur', 'Directeur'),
        ('chef_service', 'Chef de Service'),
        ('chef_division', 'Chef de Division'),
        ('autre', 'Autre'),
    ]
    
    personne = models.OneToOneField(Personne, on_delete=models.CASCADE, primary_key=True)
    grade = models.CharField(max_length=100)
    poste = models.CharField(max_length=20, choices=POSTE_CHOICES, default='autre')
    nbi_mac = models.IntegerField()  # New Bonification Index - MAC
    indice = models.IntegerField()
    anciennete_echelon = models.CharField(max_length=50)
    date_changement = models.DateField()
    anciennete_grade = models.CharField(max_length=50)
    date_nomination = models.DateField()
    date_prise_service = models.DateField()
    
    def save(self, *args, **kwargs):
        # S'assurer que le type_employe est bien 'pat'
        if self.personne:
            self.personne.type_employe = 'pat'
            self.personne.save()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Personnel PAT: {self.personne}"


class Contractuel(models.Model):
    """Modèle pour les contractuels"""
    TYPE_CONTRAT_CHOICES = [
        ('CDD', 'CDD'),
        ('CDI', 'CDI'),
        ('CONSULTANT', 'Consultant'),
        ('STAGE', 'Stage'),
    ]
    
    personne = models.OneToOneField(Personne, on_delete=models.CASCADE, primary_key=True)
    type_contrat = models.CharField(max_length=15, choices=TYPE_CONTRAT_CHOICES)
    duree_contrat = models.CharField(max_length=100)
    date_debut_contrat = models.DateField()
    date_fin_contrat = models.DateField(null=True, blank=True)
    salaire_mensuel = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # S'assurer que le type_employe est bien 'contractuel'
        if self.personne:
            self.personne.type_employe = 'contractuel'
            self.personne.save()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Contractuel: {self.personne}"


class Recrutement(models.Model):
    """Modèle pour gérer les recrutements"""
    TYPE_EMPLOYE_CHOICES = [
        ('enseignant', 'Enseignant'),
        ('pat', 'Personnel PAT'),
        ('contractuel', 'Contractuel'),
    ]
    
    STATUT_OFFRE_CHOICES = [
        ('ouverte', 'Ouverte'),
        ('fermee', 'Fermée'),
        ('pourvue', 'Pourvue'),
        ('annulee', 'Annulée'),
    ]
    
    titre_poste = models.CharField(max_length=200)
    type_employe = models.CharField(max_length=15, choices=TYPE_EMPLOYE_CHOICES)
    type_employe_specifique = models.CharField(max_length=100)
    description = models.TextField()
    requis_post = models.TextField()
    date_publication = models.DateField(auto_now_add=True)
    date_limite = models.DateField()
    date_entree_prevue = models.DateField()
    statut_offre = models.CharField(max_length=15, choices=STATUT_OFFRE_CHOICES, default='ouverte')
    service_recruteur = models.ForeignKey(Service, on_delete=models.CASCADE)
    structure_recruteur = models.ForeignKey(Structure, on_delete=models.CASCADE)
    nombre_postes = models.IntegerField(default=1)
    
    def __str__(self):
        return f"Recrutement: {self.titre_poste}"


class Candidat(models.Model):
    """Modèle pour les candidats"""
    STATUT_CANDIDATURE_CHOICES = [
        ('REÇUE', 'Reçue'),
        ('EN_EXAMEN', 'En examen'),
        ('QUALIFIÉE', 'Qualifiée'),
        ('ENTRETIEN', 'Entretien'),
        ('ACCEPTÉE', 'Acceptée'),
        ('REFUSÉE', 'Refusée'),
    ]
    
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=15)
    date_candidature = models.DateField(auto_now_add=True)
    cv = models.FileField(upload_to='cv/')
    lettre_motivation = models.FileField(upload_to='lettres/')
    statut_candidature = models.CharField(max_length=20, choices=STATUT_CANDIDATURE_CHOICES, default='REÇUE')
    recrutement = models.ForeignKey(Recrutement, on_delete=models.CASCADE, related_name='candidats')
    notes_evaluation = models.TextField(blank=True)
    date_entretien = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Candidat: {self.prenom} {self.nom}"


class Absence(models.Model):
    """Modèle pour gérer les absences"""
    TYPE_ABSENCE_CHOICES = [
        ('CONGÉ_ANNUEL', 'Congé annuel'),
        ('CONGÉ_MALADIE', 'Congé maladie'),
        ('CONGÉ_MATERNITÉ', 'Congé maternité'),
        ('DÉTACHEMENT', 'Détachement'),
        ('DISPONIBILITÉ', 'Disponibilité'),
        ('ANNÉE_SABBATIQUE', 'Année sabbatique'),
    ]
    
    STATUT_ABSENCE_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('APPROUVÉ', 'Approuvé'),
        ('REFUSÉ', 'Refusé'),
        ('ANNULÉ', 'Annulé'),
    ]
    
    personne = models.ForeignKey(Personne, on_delete=models.CASCADE, related_name='absences')
    type_absence = models.CharField(max_length=20, choices=TYPE_ABSENCE_CHOICES)
    date_debut = models.DateField()
    date_fin = models.DateField()
    statut = models.CharField(max_length=15, choices=STATUT_ABSENCE_CHOICES, default='EN_ATTENTE')
    document_justificatif = models.FileField(upload_to='justificatifs/', null=True, blank=True)
    date_demande_absence = models.DateField(auto_now_add=True)
    motif_refus = models.TextField(blank=True)
    approuve_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    commentaire_approbateur = models.TextField(blank=True)
    
    def __str__(self):
        return f"Absence {self.type_absence} - {self.personne}"
    
    def peut_approuver(self, user):
        """Vérifie si l'utilisateur peut approuver cette absence"""
        if user.role == 'admin_rh':
            return True
        if user == self.personne.get_chef_service():
            return True
        return False


class Paie(models.Model):
    """Modèle pour la gestion de la paie"""
    STATUT_PAIEMENT_CHOICES = [
        ('EN_COURS', 'En cours'),
        ('PAYÉ', 'Payé'),
        ('SUSPENDU', 'Suspendu'),
        ('ANNULÉ', 'Annulé'),
    ]
    
    personne = models.ForeignKey(Personne, on_delete=models.CASCADE, related_name='paies')
    salaire_net = models.DecimalField(max_digits=10, decimal_places=2)
    salaire_brut = models.DecimalField(max_digits=10, decimal_places=2)
    nb_enfants = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    allocations_familiales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_paiement = models.DateField()
    mois_annee = models.CharField(max_length=7)  # Format: "2024-01"
    statut_paiement = models.CharField(max_length=15, choices=STATUT_PAIEMENT_CHOICES, default='EN_COURS')
    traite_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['personne', 'mois_annee']
    
    def __str__(self):
        return f"Paie {self.mois_annee} - {self.personne}"


class Detachement(models.Model):
    """Modèle pour les détachements"""
    STATUT_DETACHEMENT_CHOICES = [
        ('EN_COURS', 'En cours'),
        ('TERMINE', 'Terminé'),
        ('ANNULE', 'Annulé'),
    ]
    
    personne = models.ForeignKey(Personne, on_delete=models.CASCADE, related_name='detachements')
    acte_detachement = models.FileField(upload_to='detachements/')
    date_debut_detachement = models.DateField()
    date_fin_detachement = models.DateField()
    structure_origine = models.ForeignKey(Structure, on_delete=models.CASCADE, related_name='detachements_sortants')
    structure_detachement = models.ForeignKey(Structure, on_delete=models.CASCADE, related_name='detachements_entrants')
    motif_detachement = models.TextField()
    statut = models.CharField(max_length=15, choices=STATUT_DETACHEMENT_CHOICES, default='EN_COURS')
    
    def __str__(self):
        return f"Détachement {self.personne} vers {self.structure_detachement}"


class Document(models.Model):
    """Modèle pour les documents"""
    TYPE_DOCUMENT_CHOICES = [
        ('CONTRAT', 'Contrat'),
        ('COTE_NOMINATION', 'Cote de nomination'),
        ('DIPLÔME', 'Diplôme'),
        ('CERTIFICAT', 'Certificat'),
        ('ÉVALUATION', 'Évaluation'),
        ('CV', 'CV'),
        ('PHOTO', 'Photo'),
    ]
    
    nom = models.CharField(max_length=200)
    type_document = models.CharField(max_length=20, choices=TYPE_DOCUMENT_CHOICES)
    chemin_fichier = models.FileField(upload_to='documents/')
    taille_fichier = models.BigIntegerField()
    date_upload = models.DateTimeField(auto_now_add=True)
    proprietaire = models.ForeignKey(Personne, on_delete=models.CASCADE, related_name='documents')
    uploade_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.nom} - {self.proprietaire}"


# Modèles de permissions personnalisées
class PermissionService(models.Model):
    """Gestion des permissions par service"""
    PERMISSION_CHOICES = [
        ('view', 'Voir'),
        ('add', 'Ajouter'),
        ('change', 'Modifier'),
        ('delete', 'Supprimer'),
        ('approve_absence', 'Approuver absences'),
        ('manage_paie', 'Gérer paie'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES)
    
    class Meta:
        unique_together = ['user', 'service', 'permission']


# Modèles d'énumération conservés et améliorés
class TypeStructure(models.Model):
    """Types de structures organisationnelles"""
    TYPE_CHOICES = [
        ('ENSEIGNEMENT', 'Enseignement'),
        ('ADMINISTRATION', 'Administration'),
        ('RECHERCHE', 'Recherche'),
        ('TECHNIQUE', 'Technique'),
    ]
    
    libelle = models.CharField(max_length=20, choices=TYPE_CHOICES, unique=True)
    
    def __str__(self):
        return self.libelle


class StatutOffre(models.Model):
    """Énumérations pour les statuts d'offre"""
    STATUT_CHOICES = [
        ('OUVERTE', 'Ouverte'),
        ('FERMEE', 'Fermée'),
        ('POURVUE', 'Pourvue'),
        ('ANNULEE', 'Annulée'),
    ]
    
    libelle = models.CharField(max_length=20, choices=STATUT_CHOICES, unique=True)
    
    def __str__(self):
        return self.libelle


class TypeContrat(models.Model):
    """Types de contrats"""
    TYPE_CHOICES = [
        ('CDD', 'CDD'),
        ('CDI', 'CDI'),
        ('CONSULTANT', 'Consultant'),
        ('STAGE', 'Stage'),
    ]
    
    libelle = models.CharField(max_length=15, choices=TYPE_CHOICES, unique=True)
    
    def __str__(self):
        return self.libelle


class TypeAbsence(models.Model):
    """Types d'absences"""
    TYPE_CHOICES = [
        ('CONGÉ_ANNUEL', 'Congé annuel'),
        ('CONGÉ_MALADIE', 'Congé maladie'),
        ('CONGÉ_MATERNITÉ', 'Congé maternité'),
        ('DÉTACHEMENT', 'Détachement'),
        ('DISPONIBILITÉ', 'Disponibilité'),
        ('ANNÉE_SABBATIQUE', 'Année sabbatique'),
    ]
    
    libelle = models.CharField(max_length=20, choices=TYPE_CHOICES, unique=True)
    
    def __str__(self):
        return self.libelle


class StatutPaiement(models.Model):
    """Statuts de paiement"""
    STATUT_CHOICES = [
        ('EN_COURS', 'En cours'),
        ('PAYÉ', 'Payé'),
        ('SUSPENDU', 'Suspendu'),
        ('ANNULÉ', 'Annulé'),
    ]
    
    libelle = models.CharField(max_length=15, choices=STATUT_CHOICES, unique=True)
    
    def __str__(self):
        return self.libelle


class StatutAbsence(models.Model):
    """Statuts d'absence"""
    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('APPROUVÉ', 'Approuvé'),
        ('REFUSÉ', 'Refusé'),
        ('ANNULÉ', 'Annulé'),
    ]
    
    libelle = models.CharField(max_length=15, choices=STATUT_CHOICES, unique=True)
    
    def __str__(self):
        return self.libelle


class TypeDocument(models.Model):
    """Types de documents"""
    TYPE_CHOICES = [
        ('CONTRAT', 'Contrat'),
        ('COTE_NOMINATION', 'Cote de nomination'),
        ('DIPLÔME', 'Diplôme'),
        ('CERTIFICAT', 'Certificat'),
        ('ÉVALUATION', 'Évaluation'),
        ('CV', 'CV'),
        ('PHOTO', 'Photo'),
    ]
    
    libelle = models.CharField(max_length=20, choices=TYPE_CHOICES, unique=True)
    
    def __str__(self):
        return self.libelle


class StatutCandidature(models.Model):
    """Statuts de candidature"""
    STATUT_CHOICES = [
        ('REÇUE', 'Reçue'),
        ('EN_EXAMEN', 'En examen'),
        ('QUALIFIÉE', 'Qualifiée'),
        ('ENTRETIEN', 'Entretien'),
        ('ACCEPTÉE', 'Acceptée'),
        ('REFUSÉE', 'Refusée'),
    ]
    
    libelle = models.CharField(max_length=20, choices=STATUT_CHOICES, unique=True)
    
    def __str__(self):
        return self.libelle