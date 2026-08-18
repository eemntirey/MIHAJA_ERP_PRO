from app.models.base import BaseModel
from app import db
from sqlalchemy import Numeric

class FactureFournisseur(BaseModel):
    __tablename__ = 'factures_fournisseur'
    
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), nullable=False, index=True)
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    total_ht = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    total_ttc = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    statut = db.Column(db.String(50), default='non_payee')  # non_payee, payee, payee_partiel, annulee
    
    # Relations
    fournisseur = db.relationship('Fournisseur', back_populates='factures')

