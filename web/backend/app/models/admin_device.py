from app.models.base import BaseModel
from app import db
from sqlalchemy import Enum
import enum
from datetime import datetime


class StatutDevice(enum.Enum):
    ACTIVE = 'active'
    REVOKED = 'revoked'


class AdminDevice(BaseModel):
    __tablename__ = 'admin_devices'

    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False, index=True)
    device_id = db.Column(db.String(255), nullable=False, index=True)
    device_name = db.Column(db.String(255))
    statut = db.Column(Enum(StatutDevice), default=StatutDevice.ACTIVE, nullable=False)
    last_seen = db.Column(db.DateTime)

    user = db.relationship('Utilisateur', backref='admin_devices', foreign_keys='AdminDevice.user_id')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['statut'] = (
            self.statut.value
            if hasattr(self.statut, 'value')
            else self.statut
        )
        return data

    def __repr__(self):
        return f'<AdminDevice {self.device_id} user={self.user_id} statut={self.statut.value if hasattr(self.statut, "value") else self.statut}>'
