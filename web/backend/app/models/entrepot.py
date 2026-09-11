from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Index


class Entrepot(BaseTenantModel):
    __tablename__ = 'entrepots'

    nom = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=True, index=True)
    adresse = db.Column(db.Text)
    ville = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    responsable = db.Column(db.String(100))
    capacite = db.Column(db.Numeric(10, 2))  # capacite de stockage totale

    principal = db.Column(db.Boolean, default=False)

    stocks = db.relationship('StockEntrepot', back_populates='entrepot', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_entrepot_nom', 'nom'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['stock_count'] = len(self.stocks.all()) if self.stocks else 0
        return data

    def __repr__(self):
        return f'<Entrepot {self.nom}>'