from sqlalchemy.exc import IntegrityError

from flask import request, current_app
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app import db
from app.security.roles import is_super_admin
from app.security.plans import check_tenant_limit
from app.security.auth import hash_password, StatutAdmin, verify_password, _validate_password
from app.security.tenant import tenant_required, get_current_tenant_id
from app.websockets.socket_events import broadcast_to_tenant
from datetime import datetime, timedelta
import secrets
import bcrypt

ns = Namespace('tenants', description='Gestion des tenants (SUPER_ADMIN)')

_ALLOWED_TENANT_FIELDS = {
    'nom', 'slug', 'domaine', 'email_contact', 'telephone',
    'adresse', 'ville', 'code_postal', 'pays', 'plan',
}


def _ensure_super_admin():
    user_id = get_jwt_identity()
    user = db.session.get(Utilisateur, user_id)
    if not user or not is_super_admin(user.role):
        return {'message': 'Acces super administrateur requis'}, 403
    return None


def _coerce_statut(value):
    if value is None: