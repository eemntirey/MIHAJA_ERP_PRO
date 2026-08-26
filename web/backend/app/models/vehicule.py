from app.models.base import BaseTenantModel
from app import db

class Vehicule(BaseTenantModel):
    __tablename__ = 'vehicules'

    marque = db.Column(db.String(100), nullable=False)
    modele = db.Column(db.String(100), nullable=False)
    plaque_immatriculation = db.Column(db.String(20), unique=True, nullable=False, index=True)
    type = db.Column(db.String(20), default='camion')  # camion/van/voiture/moto
    capacite_charge = db.Column(db.Integer)  # en kg
    capacite_volume = db.Column(db.Integer)  # en litres
    statut = db.Column(db.String(20), default='disponible')  # disponible/en_mission/en_maintenance

    chauffeur_id = db.Column(db.Integer, db.ForeignKey('livreurs.id'), index=True)

    chauffeurs = db.relationship('Livreur', back_populates='vehicule', foreign_keys='Livreur.vehicule_id')
    itineraires = db.relationship('Itineraire', back_populates='vehicule', lazy='dynamic')
    livraisons = db.relationship('Livraison', back_populates='vehicule', lazy='dynamic')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.chauffeurs:
            data['chauffeur_nom'] = self.chauffeurs.first().nom_complet if self.chauffeurs.first() else None
        return data

    def __repr__(self):
        return f'<Vehicule {self.marque} {self.modele} - {self.plaque_immatriculation}>'
