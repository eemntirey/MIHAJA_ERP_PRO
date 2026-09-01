from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Index, Numeric
import enum

class TypeCompte(enum.Enum):
    ACTIF = 'actif'
    PASSIF = 'passif'
    CHARGE = 'charge'
    PRODUIT = 'produit'

class CompteComptable(BaseTenantModel):
    __tablename__ = 'comptes_comptables'

    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nom = db.Column(db.String(100), nullable=False)
    type_compte = db.Column(db.Enum(TypeCompte, name='type_compte', values_callable=lambda e: [x.value for x in e]), nullable=False)
    sous_compte_id = db.Column(db.Integer, db.ForeignKey('comptes_comptables.id'), index=True)
    solde = db.Column(Numeric(12, 2), default=0)
    is_actif = db.Column(db.Boolean, default=True)

    sous_comptes = db.relationship('CompteComptable', remote_side='CompteComptable.id', back_populates='parent')
    parent = db.relationship('CompteComptable', remote_side='CompteComptable.sous_compte_id', back_populates='sous_comptes')
    ecritures = db.relationship('EcritureComptable', back_populates='compte', lazy='dynamic')
    tresorerie_ecritures = db.relationship('Tresorerie', back_populates='compte', foreign_keys='Tresorerie.compte_id')

    __table_args__ = (
        Index('idx_compte_numero', 'numero'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.type_compte:
            data['type_compte'] = self.type_compte.value
        if self.parent:
            data['parent_numero'] = self.parent.numero
            data['parent_nom'] = self.parent.nom
        return data

    def __repr__(self):
        return f'<CompteComptable {self.numero} - {self.nom}>'
