from datetime import datetime

from app.models.base import BaseModel
from app import db
from sqlalchemy import Numeric

class Vente(BaseModel):
    __tablename__ = 'ventes'
    
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    commercial_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), index=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total_ht = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    total_ttc = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    mode_paiement = db.Column(db.String(50))
    remarque = db.Column(db.Text)
    statut = db.Column(db.String(50), default='en_attente')  # devis, en_attente, payee, annulee
    
    # Relations
    client = db.relationship('Client', back_populates='ventes')
    commercial = db.relationship('Utilisateur', back_populates='ventes', foreign_keys='Vente.commercial_id')
    lignes_vente = db.relationship('LigneVente', back_populates='vente', lazy='dynamic')
    factures = db.relationship('Facture', back_populates='vente', lazy='dynamic')
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['total_ht'] = float(self.total_ht)
        data['total_ttc'] = float(self.total_ttc)
        return data
