from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Enum, Index
import enum

class TypeMouvement(enum.Enum):
    ENTREE = 'entree'
    SORTIE = 'sortie'
    INVENTAIRE = 'inventaire'
    AJUSTEMENT = 'ajustement'
    RETOUR = 'retour'
    TRANSFERT = 'transfert'

class MouvementStock(BaseTenantModel):
    __tablename__ = 'mouvements_stock'
    
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False, index=True)
    type_mouvement = db.Column(
        Enum(
            TypeMouvement,
            values_callable=lambda enum: [e.value for e in enum],
            name='typemouvement',
        ),
        nullable=False,
    )
    quantite = db.Column(db.Numeric(10, 2), nullable=False)
    stock_avant = db.Column(db.Numeric(10, 2))
    stock_apres = db.Column(db.Numeric(10, 2))
    raison = db.Column(db.String(200))
    reference = db.Column(db.String(50))  # Référence liée (commande, facture, etc.)
    
    # Relations
    produit = db.relationship('Produit', back_populates='mouvements_stock')
    utilisateur = db.relationship('Utilisateur', foreign_keys='MouvementStock.created_by')
    
    __table_args__ = (
        Index('idx_mouvement_produit_date', 'produit_id', 'created_at'),
        Index('idx_mouvement_type', 'type_mouvement'),
    )
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if 'type_mouvement' in data and self.type_mouvement:
            data['type_mouvement'] = self.type_mouvement.value
        if self.produit:
            data['produit_nom'] = self.produit.nom
        else:
            data['produit_nom'] = None
        return data
