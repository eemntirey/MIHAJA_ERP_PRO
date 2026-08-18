from app.models.base import BaseModel
from app import db
from sqlalchemy import Numeric

class Facture(BaseModel):
    __tablename__ = 'factures'
    
    vente_id = db.Column(db.Integer, db.ForeignKey('ventes.id'), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    total_ht = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    total_ttc = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    statut = db.Column(db.String(50), default='non_payee')  # non_payee, payee, payee_partiel, annulee
    
    # Relations
    vente = db.relationship('Vente', back_populates='factures')
    client = db.relationship('Client', back_populates='factures')
    paiements = db.relationship('Paiement', back_populates='facture', lazy='dynamic')
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['total_ht'] = float(self.total_ht)
        data['total_ttc'] = float(self.total_ttc)
        return data

