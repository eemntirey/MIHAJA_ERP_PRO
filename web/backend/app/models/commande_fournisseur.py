from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric

class CommandeFournisseur(BaseTenantModel):
    __tablename__ = 'commandes_fournisseur'
    
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), nullable=False, index=True)
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    total_ht = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    total_ttc = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    statut = db.Column(db.String(50), default='en_attente')  # en_attente, envoyee, recue, annulee
    
    # Relations
    fournisseur = db.relationship('Fournisseur', back_populates='commandes')
    lignes_achat = db.relationship('LigneAchat', back_populates='commande_fournisseur', lazy='dynamic')

