from rest_framework import serializers
from .models import (
    Structure, Personne, Enseignant, PersonnelPAT, Contractuel,
    Recrutement, Candidat, Absence, Paie, Detachement, Document,
    StatutOffre, TypeStructure, TypeEmploye, TypeContrat, TypeAbsence,
    StatutPaiement, StatutAbsence, TypeDocument, StatutCandidature
)


class StructureSerializer(serializers.ModelSerializer):
    responsable_nom = serializers.CharField(source='responsable.nom', read_only=True)
    responsable_prenom = serializers.CharField(source='responsable.prenom', read_only=True)
    parent_structure_nom = serializers.CharField(source='parent_structure.nom', read_only=True)
    
    class Meta:
        model = Structure
        fields = '__all__'


class PersonneSerializer(serializers.ModelSerializer):
    manager_nom = serializers.CharField(source='manager.nom', read_only=True)
    manager_prenom = serializers.CharField(source='manager.prenom', read_only=True)
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = Personne
        fields = '__all__'
    
    def get_age(self, obj):
        from datetime import date
        today = date.today()
        return today.year - obj.date_naissance.year - ((today.month, today.day) < (obj.date_naissance.month, obj.date_naissance.day))


class EnseignantSerializer(serializers.ModelSerializer):
    personne = PersonneSerializer(read_only=True)
    personne_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Enseignant
        fields = '__all__'


class PersonnelPATSerializer(serializers.ModelSerializer):
    personne = PersonneSerializer(read_only=True)
    personne_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = PersonnelPAT
        fields = '__all__'


class ContractuelSerializer(serializers.ModelSerializer):
    personne = PersonneSerializer(read_only=True)
    personne_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Contractuel
        fields = '__all__'


class RecrutementSerializer(serializers.ModelSerializer):
    structure_recruteur_nom = serializers.CharField(source='structure_recruteur.nom', read_only=True)
    
    class Meta:
        model = Recrutement
        fields = '__all__'


class CandidatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidat
        fields = '__all__'


class AbsenceSerializer(serializers.ModelSerializer):
    personne_nom = serializers.CharField(source='personne.nom', read_only=True)
    personne_prenom = serializers.CharField(source='personne.prenom', read_only=True)
    duree_absence = serializers.SerializerMethodField()
    
    class Meta:
        model = Absence
        fields = '__all__'
    
    def get_duree_absence(self, obj):
        return (obj.date_fin - obj.date_debut).days + 1


class PaieSerializer(serializers.ModelSerializer):
    personne_nom = serializers.CharField(source='personne.nom', read_only=True)
    personne_prenom = serializers.CharField(source='personne.prenom', read_only=True)
    
    class Meta:
        model = Paie
        fields = '__all__'


class DetachementSerializer(serializers.ModelSerializer):
    personne_nom = serializers.CharField(source='personne.nom', read_only=True)
    personne_prenom = serializers.CharField(source='personne.prenom', read_only=True)
    structure_origine_nom = serializers.CharField(source='structure_origine.nom', read_only=True)
    structure_detachement_nom = serializers.CharField(source='structure_detachement.nom', read_only=True)
    
    class Meta:
        model = Detachement
        fields = '__all__'


class DocumentSerializer(serializers.ModelSerializer):
    proprietaire_nom = serializers.CharField(source='proprietaire.nom', read_only=True)
    proprietaire_prenom = serializers.CharField(source='proprietaire.prenom', read_only=True)
    
    class Meta:
        model = Document
        fields = '__all__'


# Sérialiseurs pour les modèles d'énumération
class StatutOffreSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatutOffre
        fields = '__all__'


class TypeStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeStructure
        fields = '__all__'


class TypeEmployeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeEmploye
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


# Sérialiseurs spécialisés pour les vues complexes
class PersonneDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur détaillé pour une personne avec toutes ses relations"""
    absences = AbsenceSerializer(many=True, read_only=True)
    paies = PaieSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    detachements = DetachementSerializer(many=True, read_only=True)
    equipe = PersonneSerializer(many=True, read_only=True)
    
    class Meta:
        model = Personne
        fields = '__all__'


class StructureTreeSerializer(serializers.ModelSerializer):
    """Sérialiseur pour l'arborescence des structures"""
    sous_structures = serializers.SerializerMethodField()
    
    class Meta:
        model = Structure
        fields = '__all__'
    
    def get_sous_structures(self, obj):
        if obj.sous_structures.exists():
            return StructureTreeSerializer(obj.sous_structures.all(), many=True).data
        return []