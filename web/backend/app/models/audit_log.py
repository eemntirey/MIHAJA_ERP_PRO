from app.models.base import BaseModel
from app import db
from sqlalchemy import Enum
import enum
import json


class TypeActionAudit(enum.Enum):
    CREATION_UTILISATEUR = 'creation_utilisateur'
    CHANGEMENT_ROLE = 'changement_role'
    CREATION_EMPLOYE = 'creation_employe'
    MODIFICATION_EMPLOYE = 'modification_employe'
    SUPPRESSION_EMPLOYE = 'suppression_employe'
    CREATION_STAGIAIRE = 'creation_stagiaire'
    MODIFICATION_STAGIAIRE = 'modification_stagiaire'
    SUPPRESSION_STAGIAIRE = 'suppression_stagiaire'
    MODIFICATION_PERMISSION = 'modification_permission'
    CHANGEMENT_ABONNEMENT = 'changement_abonnements'
    CREATION_TENANT = 'creation_tenant'
    ACTIVATION_TENANT = 'activation_tenant'
    SUSPENSION_TENANT = 'suspension_tenant'
    SUPPRESSION_TENANT = 'suppression_tenant'
    PROLONGATION_ABONNEMENT = 'prolongation_abonnements'
    CONNEXION_SUPER_ADMIN = 'connexion_super_admin'
    DECONNEXION_SUPER_ADMIN = 'deconnexion_super_admin'
    MODIFICATION_TENANT = 'modification_tenant'
    ADMIN_LOGIN = 'admin_login'
    ADMIN_LOGIN_FAILED = 'admin_login_failed'
    DEVICE_REGISTERED = 'device_registered'
    DEVICE_REVOKED = 'device_revoked'
    DEVICE_CHANGE_REQUESTED = 'device_change_requested'
    ADMIN_SUSPENDED = 'admin_suspended'
    ADMIN_REACTIVATED = 'admin_reactivated'
    SUPPRESSION_UTILISATEUR = 'suppression_utilisateur'


class AuditLog(BaseModel):
    __tablename__ = 'audit_logs'

    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True, index=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True, index=True)
    type_action = db.Column(Enum(TypeActionAudit), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    metadata_json = db.Column(db.Text, nullable=True)

    tenant = db.relationship('Tenant', foreign_keys=[tenant_id], lazy='select')
    utilisateur = db.relationship('Utilisateur', foreign_keys=[utilisateur_id], lazy='select')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['type_action'] = (
            self.type_action.value
            if hasattr(self.type_action, 'value')
            else self.type_action
        )
        if self.metadata_json:
            try:
                data['metadata_json'] = json.loads(self.metadata_json)
            except (json.JSONDecodeError, TypeError):
                data['metadata_json'] = self.metadata_json
        else:
            data['metadata_json'] = None
        return data

    def __repr__(self):
        return f'<AuditLog {self.type_action} tenant={self.tenant_id} user={self.utilisateur_id}>'
