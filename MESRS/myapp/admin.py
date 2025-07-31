from django.contrib import admin
from .models import (
    Structure, Personne, Enseignant, PersonnelPAT, Contractuel,
    Recrutement, Candidat, Absence, Paie, Detachement, Document,
    StatutOffre, TypeStructure, TypeEmploye, TypeContrat, TypeAbsence,
    StatutPaiement, StatutAbsence, TypeDocument, StatutCandidature
)


@admin.register(Structure)
class StructureAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_structure', 'responsable', 'parent_structure']
    list_filter = ['type_structure']
    search_fields = ['nom', 'description']
    raw_id_fields = ['responsable', 'parent_structure']


@admin.register(Personne)
class PersonneAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prenom', 'nni', 'fonction', 'date_naissance']
    list_filter = ['genre', 'nationalite', 'situation_familiale']
    search_fields = ['nom', 'prenom', 'nni', 'fonction']
    date_hierarchy = 'date_naissance'
    raw_id_fields = ['manager']


@admin.register(Enseignant)
class EnseignantAdmin(admin.ModelAdmin):
    list_display = ['personne', 'corps', 'grade', 'echelon', 'indice']
    list_filter = ['corps', 'grade', 'echelon']
    search_fields = ['personne__nom', 'personne__prenom', 'corps', 'grade']
    date_hierarchy = 'date_entree_service_publique'


@admin.register(PersonnelPAT)
class PersonnelPATAdmin(admin.ModelAdmin):
    list_display = ['personne', 'grade', 'indice', 'nbi_mac']
    list_filter = ['grade']
    search_fields = ['personne__nom', 'personne__prenom', 'grade']
    date_hierarchy = 'date_prise_service'


@admin.register(Contractuel)
class ContractuelAdmin(admin.ModelAdmin):
    list_display = ['personne', 'type_contrat', 'date_debut_contrat', 'date_fin_contrat']
    list_filter = ['type_contrat']
    search_fields = ['personne__nom', 'personne__prenom']
    date_hierarchy = 'date_debut_contrat'


@admin.register(Recrutement)
class RecrutementAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prenom', 'type_employe', 'statut_offre', 'date_limite']
    list_filter = ['type_employe', 'statut_offre', 'structure_recruteur']
    search_fields = ['nom', 'prenom', 'description']
    date_hierarchy = 'date_limite'


@admin.register(Candidat)
class CandidatAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prenom', 'email', 'statut_candidature', 'date_candidature']
    list_filter = ['statut_candidature']
    search_fields = ['nom', 'prenom', 'email']
    date_hierarchy = 'date_candidature'


@admin.register(Absence)
class AbsenceAdmin(admin.ModelAdmin):
    list_display = ['personne', 'type_absence', 'date_debut', 'date_fin', 'statut']
    list_filter = ['type_absence', 'statut']
    search_fields = ['personne__nom', 'personne__prenom']
    date_hierarchy = 'date_debut'
    raw_id_fields = ['personne']


@admin.register(Paie)
class PaieAdmin(admin.ModelAdmin):
    list_display = ['personne', 'mois_annee', 'salaire_net', 'salaire_brut', 'statut_paiement']
    list_filter = ['statut_paiement', 'mois_annee']
    search_fields = ['personne__nom', 'personne__prenom']
    raw_id_fields = ['personne']


@admin.register(Detachement)
class DetachementAdmin(admin.ModelAdmin):
    list_display = ['personne', 'structure_origine', 'structure_detachement', 'date_debut_detachement']
    list_filter = ['structure_origine', 'structure_detachement']
    search_fields = ['personne__nom', 'personne__prenom']
    date_hierarchy = 'date_debut_detachement'
    raw_id_fields = ['personne', 'structure_origine', 'structure_detachement']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_document', 'proprietaire', 'date_upload', 'taille_fichier']
    list_filter = ['type_document', 'date_upload']
    search_fields = ['nom', 'proprietaire__nom', 'proprietaire__prenom']
    date_hierarchy = 'date_upload'
    raw_id_fields = ['proprietaire']


# Enregistrement des modèles d'énumération
admin.site.register(StatutOffre)
admin.site.register(TypeStructure)
admin.site.register(TypeEmploye)
admin.site.register(TypeContrat)
admin.site.register(TypeAbsence)
admin.site.register(StatutPaiement)
admin.site.register(StatutAbsence)
admin.site.register(TypeDocument)
admin.site.register(StatutCandidature)