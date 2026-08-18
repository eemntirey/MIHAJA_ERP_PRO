from app.models.base import BaseModel
from app import db
from sqlalchemy import Numeric

class LigneAchat(BaseModel):
    __tablename__ = 'lignes_achat'
    
    commande_fournisseur_id = db.Column(db.Integer, db.ForeignKey('commandes_fournisseur.id'), nullable=False, index=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False, index=True)
    quantite = db.Column(Numeric(10, 2), nullable=False)
    prix_unitaire_ht = db.Column(Numeric(10, 2), nullable=False)
    taux_tva = db.Column(Numeric(5, 2), default=10.00)
    total_ht = db.Column(Numeric(10, 2))
    
    # Relations
    commande_fournisseur = db.relationship('CommandeFournisseur', back_populates='lignes_achat')
    produit = db.relationship('Produit', back_populates='lignes_achat')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._calculer_total()
        
    def _calculer_total(self):
        if self.quantite and self.prix_unitaire_ht:
            self.total_ht = self.quantite * self.prix_unitaire_ht

