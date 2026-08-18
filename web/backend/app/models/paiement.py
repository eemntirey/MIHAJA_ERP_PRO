from app.models.base import BaseModel
from app import db
from sqlalchemy import Enum, Numeric
import enum


class StatutPaiement(enum.Enum):
    EN_ATTENTE = 'en_attente'
    CONFIRME = 'confirme'
    ECHEC = 'echec'
    REMBOURSE = 'rembourse'


class TypePaiement(enum.Enum):
    ABONNEMENT = 'abonnement'
    COMMANDE = 'commande'
    VENTE = 'vente'
    ACHAT = 'achat'
    SALAIRE = 'salaire'
    AUTRE = 'autre'


class Paiement(BaseModel):
    __tablename__ = 'paiements'

    facture_id = db.Column(db.Integer, db.ForeignKey('factures.id'), index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), index=True)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), index=True)
    montant = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    mode_paiement = db.Column(db.String(50), default='especes')  # espece/virement/cheque/orange_money/airtel_money
    operateur_mobile = db.Column(db.String(50))  # Orange, Airtel, etc.
    numero_telephone = db.Column(db.String(20))  # for mobile money

    devise = db.Column(db.String(10), default='MGA')
    statut = db.Column(Enum(StatutPaiement))
    type = db.Column(Enum(TypePaiement))
    reference = db.Column(db.String(100))
    id_transaction_externe = db.Column(db.String(100))
    date_paiement = db.Column(db.DateTime)
    date_echeance = db.Column(db.DateTime)  # for partial/scheduled payments
    notes = db.Column(db.Text)

    facture = db.relationship('Facture', back_populates='paiements')
    client = db.relationship('Client', back_populates='paiements')
    fournisseur = db.relationship('Fournisseur', back_populates='paiements', lazy='select')
    tenant = db.relationship('Tenant', back_populates='paiements')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['montant'] = float(self.montant) if self.montant else 0.0
        data['statut'] = (
            self.statut.value
            if hasattr(self.statut, 'value')
            else self.statut
        )
        data['type'] = (
            self.type.value
            if hasattr(self.type, 'value')
            else self.type
        )
        data['date_paiement'] = (
            self.date_paiement.isoformat()
            if self.date_paiement
            else None
        )
        return data

    def __repr__(self):
        return f'<Paiement {self.id} - {self.montant} {self.devise or "MGA"} ({self.statut.value if hasattr(self.statut, "value") else self.statut})>'
