from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Index

class Livraison(BaseTenantModel):
    __tablename__ = 'livraisons'

    vente_id = db.Column(db.Integer, db.ForeignKey('ventes.id'), index=True)
    commande_client_id = db.Column(db.Integer, db.ForeignKey('commandes_client.id'), index=True)
    itineraire_id = db.Column(db.Integer, db.ForeignKey('itineraires.id'), index=True)
    livreur_id = db.Column(db.Integer, db.ForeignKey('livreurs.id'), index=True)
    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicules.id'), index=True)

    adresse_livraison = db.Column(db.String(200))
    ville_livraison = db.Column(db.String(100))
    telephone_livraison = db.Column(db.String(20))
    nom_destinataire = db.Column(db.String(200))

    date_livraison_prevue = db.Column(db.DateTime)
    date_livraison_reelle = db.Column(db.DateTime)
    statut = db.Column(db.String(20), default='en_attente')  # en_attente/chargee/en_route/livree/retournee/echec
    signature_client = db.Column(db.Text)  # base64 image
    photo_livraison = db.Column(db.Text)  # base64 image or URL
    notes = db.Column(db.Text)

    itineraire = db.relationship('Itineraire', back_populates='livraisons')
    livreur = db.relationship('Livreur', back_populates='livraisons')
    vehicule = db.relationship('Vehicule', back_populates='livraisons')
    suivis = db.relationship('SuiviLivraison', back_populates='livraison', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_livraison_statut', 'statut'),
        Index('idx_livraison_date', 'date_livraison_prevue'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.livreur:
            data['livreur_nom'] = self.livreur.nom_complet
        if self.vehicule:
            data['vehicule_plaque'] = self.vehicule.plaque_immatriculation
        if self.itineraire:
            data['itineraire_nom'] = self.itineraire.nom
        return data

    def __repr__(self):
        return f'<Livraison {self.id} - {self.statut}>'
