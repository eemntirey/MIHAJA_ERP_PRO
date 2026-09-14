from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Index, UniqueConstraint


class StockEntrepot(BaseTenantModel):
    __tablename__ = 'stocks_entrepot'

    produit_id = db.Column(
        db.Integer,
        db.ForeignKey('produits.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    entrepot_id = db.Column(
        db.Integer,
        db.ForeignKey('entrepots.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    quantite = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    seuil_min = db.Column(db.Numeric(10, 2), default=0)
    seuil_max = db.Column(db.Numeric(10, 2))

    produit = db.relationship('Produit', back_populates='stocks_entrepot')
    entrepot = db.relationship('Entrepot', back_populates='stocks')

    __table_args__ = (
        UniqueConstraint('produit_id', 'entrepot_id', name='uq_stock_entrepot_produit_entrepot'),
        Index('idx_stock_entrepot_produit', 'produit_id', 'entrepot_id'),
        Index('idx_stock_entrepot_entrepot', 'entrepot_id'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.produit:
            data['produit_nom'] = self.produit.nom
            data['produit_reference'] = self.produit.reference
        if self.entrepot:
            data['entrepot_nom'] = self.entrepot.nom
            data['entrepot_code'] = self.entrepot.code
        return data

    def __repr__(self):
        return f'<StockEntrepot {self.produit_id}@{self.entrepot_id} = {self.quantite}>'