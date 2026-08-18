from app.models.base import BaseModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class StatutAvoir(enum.Enum):
    EN_ATTENTE = 'en_attente'
    ACCEPTE = 'accepte'
    REMBOURSE = 'rembourse'
    ANNULE = 'annule'

class Avoir(BaseModel):
    __tablename__ = 'avoirs'

    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    vente_id = db.Column(db.Integer, db.ForeignKey('ventes.id'), index=True)
    facture_id = db.Column(db.Integer, db.ForeignKey('factures.id'), index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    montant_ht = db.Column(Numeric(10, 2), nullable=False, default=0)
    montant_ttc = db.Column(Numeric(10, 2), nullable=False, default=0)
    motif = db.Column(db.Text)
    statut = db.Column(db.Enum(StatutAvoir, name='statut_avoir', values_callable=lambda e: [x.value for x in e]), default=StatutAvoir.EN_ATTENTE)
    date_avoir = db.Column(db.DateTime, default=db.func.now())
    rembourse = db.Column(db.Boolean, default=False)

    __table_args__ = (
        Index('idx_avoir_client', 'client_id'),
        Index('idx_avoir_statut', 'statut'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.statut:
            data['statut'] = self.statut.value
        return data

    def __repr__(self):
        return f'<Avoir {self.reference}>'

class Devis(BaseModel):
    __tablename__ = 'devis'

    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    commercial_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), index=True)
    total_ht = db.Column(Numeric(10, 2), nullable=False, default=0)
    total_ttc = db.Column(Numeric(10, 2), nullable=False, default=0)
    date_devis = db.Column(db.DateTime, default=db.func.now())
    date_validite = db.Column(db.DateTime)
    statut = db.Column(db.String(20), default='en_attente')  # en_attente/accepte/refuse/converti/expire
    remarque = db.Column(db.Text)
    conditions_paiement = db.Column(db.String(100))

    __table_args__ = (
        Index('idx_devis_client', 'client_id'),
        Index('idx_devis_statut', 'statut'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['total_ht'] = float(self.total_ht)
        data['total_ttc'] = float(self.total_ttc)
        return data

    def __repr__(self):
        return f'<Devis {self.reference}>'

class BonLivraison(BaseModel):
    __tablename__ = 'bons_livraison'

    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    vente_id = db.Column(db.Integer, db.ForeignKey('ventes.id'), index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    livreur_id = db.Column(db.Integer, db.ForeignKey('livreurs.id'), index=True)
    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicules.id'), index=True)
    adresse_livraison = db.Column(db.String(200))
    date_emission = db.Column(db.DateTime, default=db.func.now())
    date_livraison_prevue = db.Column(db.DateTime)
    date_livraison_reelle = db.Column(db.DateTime)
    statut = db.Column(db.String(20), default='prepare')  # prepare/expedie/livre
    signature = db.Column(db.Text)
    photo = db.Column(db.Text)
    remarque = db.Column(db.Text)

    __table_args__ = (
        Index('idx_bon_livraison_client', 'client_id'),
        Index('idx_bon_livraison_statut', 'statut'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<BonLivraison {self.reference}>'
