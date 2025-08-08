# myapp/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Service, Structure, Personne, Enseignant, PersonnelPAT, Contractuel,
    Recrutement, Candidat, Absence, Paie, Detachement, Document,
    StatutOffre, TypeStructure, TypeContrat, TypeAbsence,
    StatutPaiement, StatutAbsence, TypeDocument, StatutCandidature
)

# ========================================
# ADMIN POUR NOUVEAUX MODÈLES HIÉRARCHIQUES
# ========================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Administration des utilisateurs avec rôles"""
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations Hiérarchiques', {
            'fields': ('role', 'phone'),
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informations Hiérarchiques', {
            'fields': ('role', 'phone'),
        }),
    )

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """Administration des services"""
    list_display = ('nom', 'type_service', 'chef_service', 'nombre_employes', 'created_at')
    list_filter = ('type_service', 'created_at')
    search_fields = ('nom', 'description')
    readonly_fields = ('created_at',)
    
    def nombre_employes(self, obj):
        return obj.employes.count()
    nombre_employes.short_description = 'Nombre d\'employés'

@admin.register(Personne)
class PersonneAdmin(admin.ModelAdmin):
    """Administration des personnes"""
    list_display = ('nom', 'prenom', 'type_employe', 'service', 'fonction', 'date_embauche', 'statut_actif')
    list_filter = ('type_employe', 'service', 'genre', 'nationalite', 'statut_actif')
    search_fields = ('nom', 'prenom', 'nni', 'fonction')
    date_hierarchy = 'date_embauche'
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Informations Personnelles', {
            'fields': ('user', 'nom', 'prenom', 'date_naissance', 'lieu_naissance', 
                      'nni', 'nationalite', 'genre', 'situation_familiale', 'adresse', 'nom_pere')
        }),
        ('Formation', {
            'fields': ('dernier_diplome', 'pays_obtention_diplome', 'annee_obtention_diplome', 'specialite_formation')
        }),
        ('Informations Professionnelles', {
            'fields': ('fonction', 'type_employe', 'numero_employe', 'date_embauche', 
                      'service', 'structure', 'manager', 'statut_actif')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class EnseignantInline(admin.StackedInline):
    """Inline pour les détails enseignant"""
    model = Enseignant
    extra = 0

class PersonnelPATInline(admin.StackedInline):
    """Inline pour les détails PAT"""
    model = PersonnelPAT
    extra = 0

class ContractuelInline(admin.StackedInline):
    """Inline pour les détails contractuel"""
    model = Contractuel
    extra = 0

@admin.register(Enseignant)
class EnseignantAdmin(admin.ModelAdmin):
    """Administration des enseignants"""
    list_display = ('personne', 'grade', 'corps', 'echelon', 'indice', 'date_entree_enseignement_superieur')
    list_filter = ('grade', 'corps', 'echelon')
    search_fields = ('personne__nom', 'personne__prenom', 'corps', 'grade')
    date_hierarchy = 'date_entree_enseignement_superieur'

@admin.register(PersonnelPAT)
class PersonnelPATAdmin(admin.ModelAdmin):
    """Administration du personnel PAT"""
    list_display = ('personne', 'grade', 'poste', 'indice', 'date_nomination')
    list_filter = ('grade', 'poste')
    search_fields = ('personne__nom', 'personne__prenom', 'grade', 'poste')
    date_hierarchy = 'date_nomination'

@admin.register(Contractuel)
class ContractuelAdmin(admin.ModelAdmin):
    """Administration des contractuels"""
    list_display = ('personne', 'type_contrat', 'date_debut_contrat', 'date_fin_contrat', 'salaire_mensuel')
    list_filter = ('type_contrat', 'date_debut_contrat')
    search_fields = ('personne__nom', 'personne__prenom', 'type_contrat')
    date_hierarchy = 'date_debut_contrat'

# ========================================
# ADMIN POUR MODÈLES EXISTANTS ADAPTÉS
# ========================================

@admin.register(Structure)
class StructureAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_structure', 'service', 'parent_structure', 'responsable')
    list_filter = ('type_structure', 'service')
    search_fields = ('nom', 'description')

@admin.register(Recrutement)
class RecrutementAdmin(admin.ModelAdmin):
    list_display = ('titre_poste', 'type_employe', 'service_recruteur', 'statut_offre', 'date_limite')
    list_filter = ('type_employe', 'statut_offre', 'service_recruteur')
    search_fields = ('titre_poste', 'description')
    date_hierarchy = 'date_publication'

@admin.register(Candidat)
class CandidatAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'email', 'recrutement', 'statut_candidature', 'date_candidature')
    list_filter = ('statut_candidature', 'date_candidature')
    search_fields = ('nom', 'prenom', 'email')
    date_hierarchy = 'date_candidature'

@admin.register(Absence)
class AbsenceAdmin(admin.ModelAdmin):
    list_display = ('personne', 'type_absence', 'date_debut', 'date_fin', 'statut', 'approuve_par')
    list_filter = ('type_absence', 'statut', 'date_debut')
    search_fields = ('personne__nom', 'personne__prenom')
    date_hierarchy = 'date_debut'
    readonly_fields = ('date_demande_absence',)

@admin.register(Paie)
class PaieAdmin(admin.ModelAdmin):
    list_display = ('personne', 'mois_annee', 'salaire_net', 'salaire_brut', 'statut_paiement', 'traite_par')
    list_filter = ('mois_annee', 'statut_paiement')
    search_fields = ('personne__nom', 'personne__prenom')
    date_hierarchy = 'date_paiement'

@admin.register(Detachement)
class DetachementAdmin(admin.ModelAdmin):
    list_display = ('personne', 'structure_origine', 'structure_detachement', 'date_debut_detachement', 'statut')
    list_filter = ('statut', 'date_debut_detachement')
    search_fields = ('personne__nom', 'personne__prenom')
    date_hierarchy = 'date_debut_detachement'

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_document', 'proprietaire', 'uploade_par', 'date_upload')
    list_filter = ('type_document', 'date_upload')
    search_fields = ('nom', 'proprietaire__nom', 'proprietaire__prenom')
    date_hierarchy = 'date_upload'
    readonly_fields = ('date_upload', 'taille_fichier')

# ========================================
# ADMIN POUR MODÈLES D'ÉNUMÉRATION
# ========================================

@admin.register(StatutOffre)
class StatutOffreAdmin(admin.ModelAdmin):
    list_display = ('libelle',)

@admin.register(TypeStructure)
class TypeStructureAdmin(admin.ModelAdmin):
    list_display = ('libelle',)

@admin.register(TypeContrat)
class TypeContratAdmin(admin.ModelAdmin):
    list_display = ('libelle',)

@admin.register(TypeAbsence)
class TypeAbsenceAdmin(admin.ModelAdmin):
    list_display = ('libelle',)

@admin.register(StatutPaiement)
class StatutPaiementAdmin(admin.ModelAdmin):
    list_display = ('libelle',)

@admin.register(StatutAbsence)
class StatutAbsenceAdmin(admin.ModelAdmin):
    list_display = ('libelle',)

@admin.register(TypeDocument)
class TypeDocumentAdmin(admin.ModelAdmin):
    list_display = ('libelle',)

@admin.register(StatutCandidature)
class StatutCandidatureAdmin(admin.ModelAdmin):
    list_display = ('libelle',)

# ========================================
# CONFIGURATION DE L'ADMIN
# ========================================

# Configuration du site admin
admin.site.site_header = "Administration MESRS - Système Hiérarchique"
admin.site.site_title = "MESRS Admin"
admin.site.index_title = "Gestion des Ressources Humaines"