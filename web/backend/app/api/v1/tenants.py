from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app import db

ns = Namespace('tenants', description='Gestion des tenants (SUPER_ADMIN)')

_ALLOWED_TENANT_FIELDS = {
    'nom', 'slug', 'domaine', 'email_contact', 'telephone',
    'adresse', 'ville', 'code_postal', 'pays', 'plan',
}


def _ensure_super_admin():
    user_id = get_jwt_identity()
    user = Utilisateur.query.get(user_id)
    if not user or user.role != Role.SUPER_ADMIN:
        return {'message': 'Acces super administrateur requis'}, 403
    return None


def _coerce_statut(value):
    if value is None:
        return None
    if isinstance(value, StatutTenant):
        return value
    normalized = str(value).strip().lower()
    for member in StatutTenant:
        if member.value == normalized or member.name.lower() == normalized:
            return member
    return None


@ns.route('/')
class TenantList(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_super_admin()
        if err:
            return err
        tenants = Tenant.query.all()
        return {'tenants': [t.to_dict() for t in tenants]}, 200

    @jwt_required()
    def post(self):
        err = _ensure_super_admin()
        if err:
            return err
        data = request.get_json() or {}
        tenant = Tenant(
            nom=data.get('nom'),
            slug=data.get('slug'),
            domaine=data.get('domaine'),
            email_contact=data.get('email_contact'),
            telephone=data.get('telephone'),
            adresse=data.get('adresse'),
            ville=data.get('ville'),
            pays=data.get('pays', 'Madagascar'),
            code_postal=data.get('code_postal'),
            statut=_coerce_statut(data.get('statut', StatutTenant.ACTIF)) or StatutTenant.ACTIF,
            plan=data.get('plan', 'gratuit')
        )
        db.session.add(tenant)
        db.session.commit()
        return tenant.to_dict(), 201


@ns.route('/<int:tenant_id>')
class TenantResource(Resource):
    @jwt_required()
    def get(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouve'}, 404
        return tenant.to_dict(), 200

    @jwt_required()
    def put(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouve'}, 404
        data = request.get_json() or {}
        for key, value in data.items():
            if key in _ALLOWED_TENANT_FIELDS:
                setattr(tenant, key, value)
        if data.get('statut') is not None:
            statut = _coerce_statut(data['statut'])
            if statut is not None:
                tenant.statut = statut
        db.session.commit()
        return tenant.to_dict(), 200


@ns.route('/<int:tenant_id>/suspend')
class TenantSuspend(Resource):
    @jwt_required()
    def post(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouve'}, 404
        tenant.statut = StatutTenant.INACTIF
        tenant.is_active = False
        db.session.commit()
        return {'message': 'Tenant suspendu', 'tenant': tenant.to_dict()}, 200
