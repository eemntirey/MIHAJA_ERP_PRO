from app.models.base import BaseModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class TypePrime(enum.Enum):
    PERFORMANCE = 'performance'
    ANCIENNETE = 'anciennete'
    OBJECTIF = 'objectif'
    EXCEPTIONNEL = 'exceptionnel'

class Prime(BaseModel):
    __tablename__ = 'primes'

    employe_id = db.Column(db.Integer, db.ForeignKey('employes.id'), nullable=False, index=True)
    type_prime = db.Column(db.Enum(TypePrime, name='type_prime', values_callable=lambda e: [x.value for x in e]), nullable=False)
    montant = db.Column(Numeric(10, 2), nullable=False)
    date_octroi = db.Column(db.Date, nullable=False)
    motif = db.Column(db.String(200))

    employe = db.relationship('Employe', back_populates='primes')

    __table_args__ = (
        Index('idx_prime_employe', 'employe_id'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.type_prime:
            data['type_prime'] = self.type_prime.value
        if self.employe:
            data['employe_nom'] = self.employe.nom_complet
        return data

    def __repr__(self):
        return f'<Prime {self.employe_id} - {self.type_prime.value if self.type_prime else None}>'
