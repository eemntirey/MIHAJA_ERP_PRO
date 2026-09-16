from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Index
from datetime import date
import enum

class TypeConge(enum.Enum):
    ANNUEL = 'annuel'
    MALADIE = 'maladie'
    EXCEPTIONNEL = 'exceptionnel'
    AUTRE = 'autre'

class StatutConge(enum.Enum):
    EN_ATTENTE = 'en_attente'
    APPROUVE = 'approuve'
    REFUSE = 'refuse'
    ANNULE = 'annule'

class Conge(BaseTenantModel):
    __tablename__ = 'conges'

    employe_id = db.Column(db.Integer, db.ForeignKey('employes.id'), nullable=False, index=True)
    type_conge = db.Column(db.Enum(TypeConge, name='type_conge', values_callable=lambda e: [x.value for x in e]), default=TypeConge.ANNUEL)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)
    nb_jours = db.Column(db.Integer, nullable=False, default=1)
    annee = db.Column(db.Integer, nullable=False, index=True)
    motif = db.Column(db.String(200))
    statut = db.Column(db.Enum(StatutConge, name='statut_conge', values_callable=lambda e: [x.value for x in e]), default=StatutConge.EN_ATTENTE)

    employe = db.relationship('Employe', back_populates='conges')

    __table_args__ = (
        Index('idx_conge_employe_dates', 'employe_id', 'date_debut', 'date_fin'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.type_conge:
            data['type_conge'] = self.type_conge.value
        if self.statut:
            data['statut'] = self.statut.value
        if self.employe:
            data['employe_nom'] = self.employe.nom_complet
        data['solde_restant'] = self._solde_restant()
        return data

    def _solde_restant(self):
        total = db.session.execute(
            db.select(db.func.coalesce(db.func.sum(Conge.nb_jours), 0))
            .where(
                Conge.is_active == True,
                Conge.employe_id == self.employe_id,
                Conge.annee == self.annee,
                Conge.statut == StatutConge.APPROUVE,
            )
        ).scalar()
        credit = 30
        if self.employe is not None and self.employe.conges_credit_annuel is not None:
            credit = int(self.employe.conges_credit_annuel)
        return max(credit - int(total or 0), 0)

    @staticmethod
    def calc_jours(date_debut, date_fin):
        """Nombre de jours ouvrés (lun-ven) inclus dans [date_debut, date_fin], minimum 1."""
        import datetime as _dt
        if not date_debut or not date_fin:
            return 1
        if isinstance(date_debut, str):
            date_debut = _dt.date.fromisoformat(date_debut)
        if isinstance(date_fin, str):
            date_fin = _dt.date.fromisoformat(date_fin)
        if date_fin < date_debut:
            date_debut, date_fin = date_fin, date_debut
        nb = 0
        cur = date_debut
        while cur <= date_fin:
            if cur.weekday() < 5:
                nb += 1
            cur += _dt.timedelta(days=1)
        return max(nb, 1)

    def __repr__(self):
        return f'<Conge {self.employe_id} - {self.date_debut} → {self.date_fin} ({self.statut})>'