from app.models.base import BaseModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class TypeTresorerie(enum.Enum):
    ENTREE = 'entree'
    SORTIE = 'sortie'

class Tresorerie(BaseModel):
    __tablename__ = 'tresoreries'

    date = db.Column(db.Date, nullable=False)
    type_operation = db.Column(db.Enum(TypeTresorerie, name='type_tresorerie', values_callable=lambda e: [x.value for x in e]), nullable=False)
    montant = db.Column(Numeric(12, 2), nullable=False)
    mode_paiement = db.Column(db.String(20))  # especes/virement/cheque/mvola/orange_money/airtel_money
    libelle = db.Column(db.String(200), nullable=False)
    compte_bancaire = db.Column(db.String(100))
    reference = db.Column(db.String(50))
    piece_jointe = db.Column(db.Text)
    is_reconcilie = db.Column(db.Boolean, default=False)

    compte_id = db.Column(db.Integer, db.ForeignKey('comptes_comptables.id'), index=True)
    ecriture_id = db.Column(db.Integer, db.ForeignKey('ecritures_comptables.id'), index=True)

    compte = db.relationship('CompteComptable', back_populates='tresorerie_ecritures')
    ecriture = db.relationship('EcritureComptable', back_populates='tresorerie')

    __table_args__ = (
        Index('idx_tresorerie_date', 'date'),
        Index('idx_tresorerie_type', 'type_operation'),
        Index('idx_tresorerie_compte', 'compte_id'),
        Index('idx_tresorerie_ecriture', 'ecriture_id'),
        Index('idx_tresorerie_reconcilie', 'is_reconcilie', 'date'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.type_operation:
            data['type_operation'] = self.type_operation.value
        if self.compte:
            data['compte_numero'] = self.compte.numero
            data['compte_nom'] = self.compte.nom
        if self.ecriture:
            data['ecriture_libelle'] = self.ecriture.libelle
            data['ecriture_statut'] = self.ecriture.statut.value if self.ecriture.statut else None
        return data

    def __repr__(self):
        return f'<Tresorerie {self.date} - {self.type_operation.value if self.type_operation else None} {self.montant}>'
