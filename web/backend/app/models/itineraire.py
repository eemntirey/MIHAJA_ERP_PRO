from app.models.base import BaseModel
from app import db
from sqlalchemy import Index

class Itineraire(BaseModel):
    __tablename__ = 'itineraires'

    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    date_depart = db.Column(db.DateTime, nullable=False)
    date_retour = db.Column(db.DateTime)
    points_intermediaires = db.Column(db.Text)  # JSON text
    statut = db.Column(db.String(20), default='planifie')  # planifie/en_cours/termine/annule

    livreur_id = db.Column(db.Integer, db.ForeignKey('livreurs.id'), nullable=False, index=True)
    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicules.id'), nullable=False, index=True)

    livreur = db.relationship('Livreur', back_populates='itineraires')
    vehicule = db.relationship('Vehicule', back_populates='itineraires')
    livraisons = db.relationship('Livraison', back_populates='itineraire', lazy='dynamic')

    __table_args__ = (
        Index('idx_itineraire_date', 'date_depart'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.livreur:
            data['livreur_nom'] = self.livreur.nom_complet
        if self.vehicule:
            data['vehicule_plaque'] = self.vehicule.plaque_immatriculation
        return data

    def __repr__(self):
        return f'<Itineraire {self.nom}>'
