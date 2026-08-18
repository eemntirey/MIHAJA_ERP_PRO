from app.models.base import BaseModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class StatutPaiementSalaire(enum.Enum):
    NON_PAYE = 'non_paye'
    PARTIEL = 'partiel'
    PAYE = 'paye'

class Salaire(BaseModel):
    __tablename__ = 'salaires'

    employe_id = db.Column(db.Integer, db.ForeignKey('employes.id'), nullable=False, index=True)
    mois = db.Column(db.Integer, nullable=False)
    annee = db.Column(db.Integer, nullable=False)
    salaire_base = db.Column(Numeric(10, 2), nullable=False, default=0)
    primes = db.Column(Numeric(10, 2), default=0)
    indemnites = db.Column(Numeric(10, 2), default=0)
    deductions = db.Column(Numeric(10, 2), default=0)
    avances = db.Column(Numeric(10, 2), default=0)
    salaire_brut = db.Column(Numeric(10, 2))
    salaire_net = db.Column(Numeric(10, 2))
    statut_paiement = db.Column(db.Enum(StatutPaiementSalaire, name='statut_paiement_salaire', values_callable=lambda e: [x.value for x in e]), default=StatutPaiementSalaire.NON_PAYE)
    date_paiement = db.Column(db.Date)
    mode_paiement = db.Column(db.String(20))
    reference_paiement = db.Column(db.String(50))
    notes = db.Column(db.Text)

    employe = db.relationship('Employe', back_populates='salaires')

    __table_args__ = (
        Index('idx_salaire_employe_mois', 'employe_id', 'mois', 'annee', unique=True),
    )

    def calculer_salaire(self):
        self.salaire_brut = self.salaire_base + self.primes + self.indemnites - self.deductions
        self.salaire_net = self.salaire_brut - self.avances

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.statut_paiement:
            data['statut_paiement'] = self.statut_paiement.value
        if self.employe:
            data['employe_nom'] = self.employe.nom_complet
            data['employe_matricule'] = self.employe.matricule
        return data

    def __repr__(self):
        return f'<Salaire {self.employe_id} {self.mois}/{self.annee}>'
