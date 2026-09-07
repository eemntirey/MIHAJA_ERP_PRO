from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class TypeContratStagiaire(enum.Enum):
    STAGE_INITIATION = 'stage_initiation'
    STAGE_FIN_ETUDES = 'stage_fin_etudes'
    STAGE_PROFESSIONNEL = 'stage_professionnel'
    APPRENTISSAGE = 'apprentissage'

class SexeStagiaire(enum.Enum):
    M = 'M'
    F = 'F'

class StatutStagiaire(enum.Enum):
    ACTIF = 'actif'
    INACTIF = 'inactif'
    EN_STAGE = 'en_stage'
    TERMINE = 'termine'
    ABANDON = 'abandon'

class Stagiaire(BaseTenantModel):
    __tablename__ = 'stagiaires'

    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    matricule = db.Column(db.String(30), unique=True, nullable=False, index=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    date_naissance = db.Column(db.Date)
    lieu_naissance = db.Column(db.String(100))
    sexe = db.Column(db.Enum(SexeStagiaire, name='sexe_stagiaire', values_callable=lambda e: [x.value for x in e]), default=SexeStagiaire.M)
    adresse = db.Column(db.String(200))
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    etablissement = db.Column(db.String(150))
    formation = db.Column(db.String(150))
    type_contrat = db.Column(db.Enum(TypeContratStagiaire, name='type_contrat_stagiaire', values_callable=lambda e: [x.value for x in e]), default=TypeContratStagiaire.STAGE_INITIATION)
    date_debut = db.Column(db.Date)
    date_fin = db.Column(db.Date)
    indemnite = db.Column(Numeric(10, 2), default=0)
    tuteur_id = db.Column(db.Integer, db.ForeignKey('employes.id'))
    departement = db.Column(db.String(100))
    note = db.Column(db.Text)
    statut = db.Column(db.Enum(StatutStagiaire, name='statut_stagiaire', values_callable=lambda e: [x.value for x in e]), default=StatutStagiaire.ACTIF)

    tenant = db.relationship('Tenant', back_populates='stagiaires', lazy='select')
    tuteur = db.relationship('Employe', foreign_keys=[tuteur_id], lazy='select')

    __table_args__ = (
        Index('idx_stagiaire_matricule', 'matricule'),
        Index('idx_stagiaire_nom_prenom', 'nom', 'prenom'),
    )

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.sexe:
            data['sexe'] = self.sexe.value
        if self.type_contrat:
            data['type_contrat'] = self.type_contrat.value
        if self.statut:
            data['statut'] = self.statut.value
        data['nom_complet'] = self.nom_complet
        return data

    def __repr__(self):
        return f'<Stagiaire {self.matricule} - {self.nom_complet}>'
