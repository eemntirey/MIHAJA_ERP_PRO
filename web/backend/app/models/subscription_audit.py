from app.models.base import BaseModel
from app import db
from sqlalchemy import Text, DateTime, ForeignKey
from datetime import datetime


class SubscriptionAuditTrail(BaseModel):
    __tablename__ = 'subscription_audit_trails'

    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    abonnement_id = db.Column(db.Integer, db.ForeignKey('abonnements.id'), nullable=True)
    date_changement = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ancien_plan = db.Column(db.String(50), nullable=True)
    nouveau_plan = db.Column(db.String(50), nullable=False)
    declencheur = db.Column(db.String(20), nullable=False)  # automatique | manuel
    description = db.Column(db.Text, nullable=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True)

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['date_changement'] = (
            self.date_changement.isoformat()
            if self.date_changement else None
        )
        return data

    def __repr__(self):
        return (
            f'<SubscriptionAuditTrail tenant={self.tenant_id} '
            f'plan={self.nouveau_plan} trigger={self.declencheur}>'
        )
