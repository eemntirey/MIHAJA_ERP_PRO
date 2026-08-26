from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class StatutEcriture(enum.Enum):
    BROUILLON = 'brouillon'
    VALIDE = 'valide'
    ANNULE = 'annule'

class EcritureComptable(BaseTenantModel):
    __tablename__ = 'ecritures_comptables'

    date = db.Column(db.Date, nullable=False)
    compte_id = db.Column(db.Integer, db.ForeignKey('comptes_comptables.id'), nullable=False, index=True)
    montant_debit = db.Column(Numeric(12, 2), default=0)
    montant_credit = db.Column(Numeric(12, 2), default=0)
    libelle = db.Column(db.String(200), nullable=False)
    piece_joint = db.Column(db.Text)
    reference_externe = db.Column(db.String(50))  # facture_id, vente_id, etc.
    entite_type = db.Column(db.String(50))  # vente, facture, achat, etc.
    entite_id = db.Column(db.Integer, index=True)
    statut = db.Column(db.Enum(StatutEcriture, name='statut_ecriture', values_callable=lambda e: [x.value for x in e]), default=StatutEcriture.BROUILLON)
    ecriture_annulee_id = db.Column(db.Integer, db.ForeignKey('ecritures_comptables.id'), index=True)

    compte = db.relationship('CompteComptable', back_populates='ecritures', foreign_keys=[compte_id])
    ecriture_annulee = db.relationship('EcritureComptable', remote_side='EcritureComptable.id', back_populates='annulations')
    annulations = db.relationship('EcritureComptable', foreign_keys=[ecriture_annulee_id], back_populates='ecriture_annulee')
    tresorerie = db.relationship('Tresorerie', back_populates='ecriture', foreign_keys='Tresorerie.ecriture_id')

    __table_args__ = (
        Index('idx_ecriture_date', 'date'),
        Index('idx_ecriture_reference', 'reference_externe', 'entite_type', 'entite_id'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.statut:
            data['statut'] = self.statut.value
        if self.compte:
            data['compte_numero'] = self.compte.numero
            data['compte_nom'] = self.compte.nom
        if self.tresorerie:
            data['tresorerie_ids'] = [t.id for t in self.tresorerie]
            data['tresorerie_count'] = len(self.tresorerie)
        return data

    def __repr__(self):
        return f'<EcritureComptable {self.id} - {self.libelle}>'
