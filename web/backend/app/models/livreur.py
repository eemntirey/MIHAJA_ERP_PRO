from app.models.base import BaseModel
from app import db
from sqlalchemy import Numeric, Index

class Livreur(BaseModel):
    __tablename__ = 'livreurs'

    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    numero_permis = db.Column(db.String(50))
    date_embauche = db.Column(db.DateTime)
    statut = db.Column(db.String(20), default='actif')  # actif/inactif/en_conges

    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicules.id'), index=True)

    vehicule = db.relationship('Vehicule', back_populates='chauffeurs', foreign_keys='Livreur.vehicule_id')
    itineraires = db.relationship('Itineraire', back_populates='livreur', lazy='dynamic')
    livraisons = db.relationship('Livraison', back_populates='livreur', lazy='dynamic')

    __table_args__ = (
        Index('idx_livreur_nom', 'nom', 'prenom'),
    )

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['nom_complet'] = self.nom_complet
        return data

    def __repr__(self):
        return f'<Livreur {self.nom_complet}>'
