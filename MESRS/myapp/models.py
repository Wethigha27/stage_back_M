from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Structure(models.Model):
    """Modèle pour les structures organisationnelles"""
    nom = models.CharField(max_length=255)
    responsable = models.ForeignKey('Personne', on_delete=models.SET_NULL, null=True, blank=True, related_name='structures_dirigees')
    type_structure = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent_structure = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sous_structures')
    
    def __str__(self):
        return self.nom


class Personne(models.Model):
    """Modèle de base pour toutes les personnes du système"""
    GENRE_CHOICES = [
        ('MASCULIN', 'Masculin'),
        ('FEMININ', 'Féminin'),
    ]
    
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
    dernier_diplome = models.CharField(max_length=200)
    pays_obtention_diplome = models.CharField(max_length=100)
    annee_obtention_diplome = models.IntegerField()
    specialite_formation = models.CharField(max_length=200)
    fonction = models.CharField(max_length=100)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='equipe')
    
    def __str__(self):
        return f"{self.prenom} {self.nom}"


class Enseignant(models.Model):
    """Modèle pour les enseignants"""
    personne = models.OneToOneField(Personne, on_delete=models.CASCADE, primary_key=True)
    corps = models.CharField(max_length=100)
    grade = models.CharField(max_length=100)
    echelon = models.CharField(max_length=50)
    indice = models.IntegerField()
    date_entree_service_publique = models.DateField()
    date_entree_enseignement_superieur = models.DateField()
    date_fin_service_obligatoire = models.DateField()
    
    def __str__(self):
        return f"Enseignant: {self.personne}"


class PersonnelPAT(models.Model):
    """Modèle pour le Personnel Administratif et Technique"""
    personne = models.OneToOneField(Personne, on_delete=models.CASCADE, primary_key=True)
    grade = models.CharField(max_length=100)
    nbi_mac = models.IntegerField()  # New Bonification Index - MAC
    indice = models.IntegerField()
    anciennete_echelon = models.CharField(max_length=50)
    date_changement = models.DateField()
    anciennete_grade = models.CharField(max_length=50)
    date_nomination = models.DateField()
    date_prise_service = models.DateField()
    
    def __str__(self):
        return f"Personnel PAT: {self.personne}"


class Recrutement(models.Model):
    """Modèle pour gérer les recrutements"""
    TYPE_EMPLOYE_CHOICES = [
        ('ENSEIGNANT', 'Enseignant'),
        ('PERSONNEL_PAT', 'Personnel PAT'),
        ('CONTRACTUEL', 'Contractuel'),
    ]
    
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    type_employe = models.CharField(max_length=20, choices=TYPE_EMPLOYE_CHOICES)
    type_employe_specifique = models.CharField(max_length=100)
    description = models.TextField()
    requis_post = models.TextField()
    date_limite = models.DateField()
    date_entree = models.DateField()
    statut_offre = models.CharField(max_length=50)
    structure_recruteur = models.ForeignKey(Structure, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"Recrutement: {self.nom} {self.prenom}"


class StatutOffre(models.Model):
    """Énumérations pour les statuts d'offre"""
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
    date_candidature = models.DateField()
    cv = models.FileField(upload_to='cv/')
    lettre_motivation = models.FileField(upload_to='lettres/')
    statut_candidature = models.CharField(max_length=20, choices=STATUT_CANDIDATURE_CHOICES)
    
    def __str__(self):
        return f"Candidat: {self.prenom} {self.nom}"


class Contractuel(models.Model):
    """Modèle pour les contractuels"""
    TYPE_CONTRAT_CHOICES = [
        ('CDD', 'CDD'),
        ('CDI', 'CDI'),
    ]
    
    personne = models.OneToOneField(Personne, on_delete=models.CASCADE, primary_key=True)
    type_contrat = models.CharField(max_length=10, choices=TYPE_CONTRAT_CHOICES)
    duree_contrat = models.CharField(max_length=100)
    date_debut_contrat = models.DateField()
    date_fin_contrat = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"Contractuel: {self.personne}"


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
    statut = models.CharField(max_length=15, choices=STATUT_ABSENCE_CHOICES)
    document_justificatif = models.FileField(upload_to='justificatifs/', null=True, blank=True)
    date_demande_absence = models.DateField()
    motif_refus = models.TextField(blank=True)
    
    def __str__(self):
        return f"Absence {self.type_absence} - {self.personne}"


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
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_paiement = models.DateField()
    mois_annee = models.CharField(max_length=7)  # Format: "2024-01"
    statut_paiement = models.CharField(max_length=15, choices=STATUT_PAIEMENT_CHOICES)
    
    class Meta:
        unique_together = ['personne', 'mois_annee']
    
    def __str__(self):
        return f"Paie {self.mois_annee} - {self.personne}"


class Detachement(models.Model):
    """Modèle pour les détachements"""
    personne = models.ForeignKey(Personne, on_delete=models.CASCADE, related_name='detachements')
    acte_detachement = models.FileField(upload_to='detachements/')
    date_debut_detachement = models.DateField()
    date_fin_detachement = models.DateField()
    structure_origine = models.ForeignKey(Structure, on_delete=models.CASCADE, related_name='detachements_sortants')
    structure_detachement = models.ForeignKey(Structure, on_delete=models.CASCADE, related_name='detachements_entrants')
    motif_detachement = models.TextField()
    
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
    ]
    
    nom = models.CharField(max_length=200)
    type_document = models.CharField(max_length=20, choices=TYPE_DOCUMENT_CHOICES)
    chemin_fichier = models.FileField(upload_to='documents/')
    taille_fichier = models.BigIntegerField()
    date_upload = models.DateTimeField(auto_now_add=True)
    proprietaire = models.ForeignKey(Personne, on_delete=models.CASCADE, related_name='documents')
    
    def __str__(self):
        return f"{self.nom} - {self.proprietaire}"


# Modèles d'énumération pour les choix
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


class TypeEmploye(models.Model):
    """Types d'employés"""
    TYPE_CHOICES = [
        ('ENSEIGNANT', 'Enseignant'),
        ('PERSONNEL_PAT', 'Personnel PAT'),
        ('CONTRACTUEL', 'Contractuel'),
    ]
    
    libelle = models.CharField(max_length=20, choices=TYPE_CHOICES, unique=True)
    
    def __str__(self):
        return self.libelle


class TypeContrat(models.Model):
    """Types de contrats"""
    TYPE_CHOICES = [
        ('CDD', 'CDD'),
        ('CDI', 'CDI'),
    ]
    
    libelle = models.CharField(max_length=10, choices=TYPE_CHOICES, unique=True)
    
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