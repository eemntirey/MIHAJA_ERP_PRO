from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index, event
from sqlalchemy.orm import object_session


class Livreur(BaseTenantModel):
    __tablename__ = 'livreurs'

    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    numero_permis = db.Column(db.String(50))
    date_embauche = db.Column(db.DateTime)
    statut = db.Column(db.String(20), default='actif')  # actif/inactif/en_conges

    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True, index=True, unique=True)

    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicules.id'), index=True)

    utilisateur = db.relationship('Utilisateur', backref='livreur_profile', foreign_keys='Livreur.utilisateur_id')
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


@event.listens_for(Livreur, 'before_insert')
@event.listens_for(Livreur, 'before_update')
def _livreur_check_tenant_consistency(mapper, connection, target):
    if not target.utilisateur_id:
        return
    from app.models.utilisateur import Utilisateur
    session = object_session(target)
    if session is None:
        return
    user = session.get(Utilisateur, target.utilisateur_id)
    if user is None:
        raise ValueError(f"Livreur.utilisateur_id={target.utilisateur_id} ne reference aucun utilisateur")
    if target.tenant_id and user.tenant_id and target.tenant_id != user.tenant_id:
        raise ValueError(
            "Cross-tenant interdit : Livreur.tenant_id != Utilisateur.tenant_id"
        )
