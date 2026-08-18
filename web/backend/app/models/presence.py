from app.models.base import BaseModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class StatutPresence(enum.Enum):
    PRESENT = 'present'
    ABSENT = 'absent'
    EN_RETARD = 'en_retard'
    CONGE = 'conge'
    MALADIE = 'maladie'

class Presence(BaseModel):
    __tablename__ = 'presences'

    employe_id = db.Column(db.Integer, db.ForeignKey('employes.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)
    heure_arrivee = db.Column(db.DateTime)
    heure_depart = db.Column(db.DateTime)
    heure_pause_debut = db.Column(db.DateTime)
    heure_pause_fin = db.Column(db.DateTime)
    heures_travaillees = db.Column(db.Numeric(4, 2))
    heures_supplementaires = db.Column(db.Numeric(4, 2), default=0)
    statut = db.Column(db.Enum(StatutPresence, name='statut_presence', values_callable=lambda e: [x.value for x in e]), default=StatutPresence.PRESENT)
    remarque = db.Column(db.String(200))

    employe = db.relationship('Employe', back_populates='presences')

    __table_args__ = (
        Index('idx_presence_employe_date', 'employe_id', 'date', unique=True),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.statut:
            data['statut'] = self.statut.value
        if self.employe:
            data['employe_nom'] = self.employe.nom_complet
        return data

    def __repr__(self):
        return f'<Presence {self.employe_id} - {self.date}>'
