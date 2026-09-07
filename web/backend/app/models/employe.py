from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class TypeContrat(enum.Enum):
    CDI = 'cdi'
    CDD = 'cdd'
    STAGE = 'stage'
    FREELANCE = 'freelance'

class Sexe(enum.Enum):
    M = 'M'
    F = 'F'

class StatutEmploye(enum.Enum):
    ACTIF = 'actif'
    INACTIF = 'inactif'
    EN_CONGE = 'en_conges'
    DEPART = 'depart'

class Employe(BaseTenantModel):
    __tablename__ = 'employes'

    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    matricule = db.Column(db.String(30), unique=True, nullable=False, index=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    date_naissance = db.Column(db.Date)
    lieu_naissance = db.Column(db.String(100))
    sexe = db.Column(db.Enum(Sexe, name='sexe', values_callable=lambda e: [x.value for x in e]), default=Sexe.M)
    adresse = db.Column(db.String(200))
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    numero_securite_sociale = db.Column(db.String(50))

    poste = db.Column(db.String(100))
    departement = db.Column(db.String(100))

    date_embauche = db.Column(db.Date)
    date_fin_contrat = db.Column(db.Date)
    type_contrat = db.Column(db.Enum(TypeContrat, name='type_contrat', values_callable=lambda e: [x.value for x in e]), default=TypeContrat.CDI)

    salaire_base = db.Column(Numeric(10, 2), default=0)
    coefficient = db.Column(db.String(20))
    anciennete = db.Column(db.Integer, default=0)

    banque_nom = db.Column(db.String(100))
    banque_iban = db.Column(db.String(50))
    banque_bic = db.Column(db.String(20))

    photo = db.Column(db.Text)
    statut = db.Column(db.Enum(StatutEmploye, name='statut_employe', values_callable=lambda e: [x.value for x in e]), default=StatutEmploye.ACTIF)

    notes = db.Column(db.Text)

    presences = db.relationship('Presence', back_populates='employe', lazy='dynamic')
    salaires = db.relationship('Salaire', back_populates='employe', lazy='dynamic')
    primes = db.relationship('Prime', back_populates='employe', lazy='dynamic')

    tenant = db.relationship('Tenant', back_populates='employes', lazy='select')

    __table_args__ = (
        Index('idx_employe_matricule', 'matricule'),
        Index('idx_employe_nom_prenom', 'nom', 'prenom'),
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
        return f'<Employe {self.matricule} - {self.nom_complet}>'
