from app.models.base import BaseTenantModel
from app import db

class SuiviLivraison(BaseTenantModel):
    __tablename__ = 'suivis_livraison'

    livraison_id = db.Column(db.Integer, db.ForeignKey('livraisons.id'), nullable=False, index=True)
    statut = db.Column(db.String(50), nullable=False)
    localisation_lat = db.Column(db.Numeric(10, 8))
    localisation_lng = db.Column(db.Numeric(11, 8))
    commentaire = db.Column(db.Text)
    date_mise_a_jour = db.Column(db.DateTime, default=db.func.now())

    livraison = db.relationship('Livraison', back_populates='suivis')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<SuiviLivraison {self.livraison_id} - {self.statut}>'
