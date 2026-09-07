from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class StatutCommandeAchat(enum.Enum):
    BROUILLON = 'brouillon'
    ENVOYEE = 'envoyee'
    CONFIRMEE = 'confirmee'
    RECUE = 'recue'
    PARTIELLEMENT_RECUE = 'partiellement_recue'
    ANNULEE = 'annulee'

class CommandeAchat(BaseTenantModel):
    __tablename__ = 'commandes_achat'

    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), nullable=False, index=True)
    total_ht = db.Column(Numeric(12, 2), nullable=False, default=0)
    total_ttc = db.Column(Numeric(12, 2), nullable=False, default=0)
    statut = db.Column(db.Enum(StatutCommandeAchat, name='statut_commande_achat', values_callable=lambda e: [x.value for x in e]), default=StatutCommandeAchat.BROUILLON)
    date_commande = db.Column(db.DateTime, default=db.func.now())
    date_livraison_prevue = db.Column(db.DateTime)
    date_reception = db.Column(db.DateTime)
    remarque = db.Column(db.Text)
    conditions_paiement = db.Column(db.String(100))

    fournisseur = db.relationship('Fournisseur', back_populates='commandes_achat')
    receptions = db.relationship('ReceptionAchat', back_populates='commande_achat', lazy='dynamic')
    lignes_achat = db.relationship('LigneAchat', back_populates='commande_achat', lazy='dynamic')

    __table_args__ = (
        Index('idx_commande_achat_statut', 'statut'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.statut:
            data['statut'] = self.statut.value
        if self.fournisseur:
            data['fournisseur_nom'] = self.fournisseur.nom_complet
        return data

    def __repr__(self):
        return f'<CommandeAchat {self.reference}>'

class ReceptionAchat(BaseTenantModel):
    __tablename__ = 'receptions_achat'

    commande_achat_id = db.Column(db.Integer, db.ForeignKey('commandes_achat.id'), nullable=False, index=True)
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    date_reception = db.Column(db.DateTime, default=db.func.now())
    receptionne_par_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), index=True)
    quantite_recue = db.Column(Numeric(10, 2), nullable=False)
    quantite_commandee = db.Column(Numeric(10, 2), nullable=False)
    ecart = db.Column(Numeric(10, 2))
    remarque = db.Column(db.Text)

    commande_achat = db.relationship('CommandeAchat', back_populates='receptions')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<ReceptionAchat {self.reference}>'

class QualiteAchat(BaseTenantModel):
    __tablename__ = 'qualites_achat'

    reception_id = db.Column(db.Integer, db.ForeignKey('receptions_achat.id'), nullable=False, index=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False, index=True)
    quantite_controlee = db.Column(Numeric(10, 2), nullable=False)
    quantite_conforme = db.Column(Numeric(10, 2), nullable=False)
    quantite_rejetee = db.Column(Numeric(10, 2), default=0)
    motif_rejet = db.Column(db.String(200))
    statut = db.Column(db.String(20), default='conforme')  # conforme/non_conforme
    remarque = db.Column(db.Text)

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<QualiteAchat {self.id}>'
