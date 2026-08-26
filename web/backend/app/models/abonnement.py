from app.models.base import BaseModel
from app import db
from sqlalchemy import Enum, Numeric
import enum
from datetime import datetime


class StatutAbonnement(enum.Enum):
    ACTIF = 'actif'
    EXPIRE = 'expire'
    EN_ATTENTE = 'en_attente'
    ANNULE = 'annule'


class Abonnement(BaseModel):
    __tablename__ = 'abonnements'

    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    montant = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    devise = db.Column(db.String(10), default='MGA')
    date_debut = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_fin = db.Column(db.DateTime, nullable=False)
    statut = db.Column(Enum(StatutAbonnement), default=StatutAbonnement.EN_ATTENTE, nullable=False)
    methode_paiement = db.Column(db.String(50))
    reference_paiement = db.Column(db.String(100))
    plan = db.Column(db.String(50))
    notes = db.Column(db.Text)

    max_utilisateurs = db.Column(db.Integer, nullable=True)
    max_produits = db.Column(db.Integer, nullable=True)
    max_clients = db.Column(db.Integer, nullable=True)
    max_admins = db.Column(db.Integer, nullable=True)
    max_employees = db.Column(db.Integer, nullable=True)
    max_interns = db.Column(db.Integer, nullable=True)
    max_tenants = db.Column(db.Integer, nullable=True)
    modules = db.Column(db.Text, nullable=True)

    tenant = db.relationship('Tenant', back_populates='abonnements', lazy='select')
    paiements = db.relationship('Paiement', back_populates='abonnement', cascade='all, delete-orphan')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['statut'] = (
            self.statut.value
            if hasattr(self.statut, 'value')
            else self.statut
        )
        data['montant'] = float(self.montant) if self.montant else 0.0
        data['date_debut'] = (
            self.date_debut.isoformat()
            if self.date_debut
            else None
        )
        data['date_fin'] = (
            self.date_fin.isoformat()
            if self.date_fin
            else None
        )
        data['modules'] = (
            [m.strip() for m in self.modules.split(',') if m.strip()]
            if isinstance(self.modules, str)
            else self.modules
        )
        return data

    def __repr__(self):
        return f'<Abonnement {self.id} - Tenant {self.tenant_id} ({self.statut.value if hasattr(self.statut, "value") else self.statut})>'
