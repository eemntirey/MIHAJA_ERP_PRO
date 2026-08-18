from app.models.base import BaseModel
from app import db
from sqlalchemy import Numeric

class LigneVente(BaseModel):
    __tablename__ = 'lignes_vente'
    
    vente_id = db.Column(db.Integer, db.ForeignKey('ventes.id'), nullable=False, index=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False, index=True)
    quantite = db.Column(Numeric(10, 2), nullable=False)
    prix_unitaire_ht = db.Column(Numeric(10, 2), nullable=False)
    prix_unitaire_ttc = db.Column(Numeric(10, 2))
    taux_tva = db.Column(Numeric(5, 2), default=10.00)
    remise = db.Column(Numeric(5, 2), default=0.00)
    total_ht = db.Column(Numeric(10, 2))
    total_ttc = db.Column(Numeric(10, 2))
    
    # Relations
    vente = db.relationship('Vente', back_populates='lignes_vente')
    produit = db.relationship('Produit', back_populates='lignes_vente')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._calculer_totaux()
        
    def _calculer_totaux(self):
        if self.prix_unitaire_ht is not None and self.taux_tva is not None:
            self.prix_unitaire_ttc = self.prix_unitaire_ht * (1 + self.taux_tva / 100)
        if self.quantite is not None and self.prix_unitaire_ht is not None:
            base_ht = self.quantite * self.prix_unitaire_ht
            if self.remise is not None:
                base_ht = base_ht * (1 - self.remise / 100)
            self.total_ht = base_ht
            if self.taux_tva is not None:
                self.total_ttc = base_ht * (1 + self.taux_tva / 100)
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.produit:
            data['produit_nom'] = self.produit.nom
        else:
            data['produit_nom'] = None
        return data

