from flask import request, current_app
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app import db
from app.security.roles import is_super_admin
from app.security.plans import check_tenant_limit
from app.security.auth import hash_password, StatutAdmin, verify_password
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
        now = datetime.utcnow()
        trial_duration = timedelta(days=14)
        plan = data.get('plan', 'gratuit')

        allowed, message = check_tenant_limit(plan)
        if not allowed:
            return {'message': message}, 403

        admin_email = data.get('admin_email')
        admin_password = data.get('admin_password')
        admin_nom = data.get('admin_nom')
        admin_prenom = data.get('admin_prenom')

        if not admin_email or not admin_password:
            return {'message': 'admin_email et admin_password sont requis pour creer l\'admin principal'}, 400

        try:
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
                statut=_coerce_statut(data.get('statut', StatutTenant.EN_ESSAI)) or StatutTenant.EN_ESSAI,
                plan=plan,
                date_debut_essai=now,
                date_fin_essai=now + trial_duration,
            )
            db.session.add(tenant)
            db.session.flush()

            admin_username = data.get('admin_username') or admin_email
            if Utilisateur.query.filter(
                Utilisateur.is_active == True,
                (Utilisateur.email == admin_email) | (Utilisateur.username == admin_username)
            ).first():
                db.session.rollback()
                return {'message': 'Un compte avec cet email ou nom d\'utilisateur existe deja'}, 409

            admin = Utilisateur(
                username=admin_username,
                email=admin_email,
                password_hash=hash_password(admin_password),
                nom=admin_nom,
                prenom=admin_prenom,
                role=Role.ADMIN,
                statut=StatutUtilisateur.ACTIF,
                admin_statut=StatutAdmin.ACTIVE,
                tenant_id=tenant.id,
                is_principal_admin=True,
            )
            db.session.add(admin)
            db.session.flush()

            tenant.admin_principal_id = admin.id
            db.session.add(tenant)
            db.session.flush()

            from app.services.abonnement_service import AbonnementService
            AbonnementService.create_abonnement({
                'tenant_id': tenant.id,
                'plan': plan,
            })

            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            current_app.logger.exception(
                'Erreur lors de la creation du tenant (plan=%s): %s', plan, exc
            )
            return {'message': 'Erreur lors de la creation du tenant. Verifiez les champs (slug/domaine uniques).'}, 500

        try:
            broadcast_to_tenant(tenant.id, 'tenant:updated', tenant.to_dict())
        except Exception:
            pass
        return {
            'tenant': tenant.to_dict(),
            'admin': {
                'id': admin.id,
                'username': admin.username,
                'email': admin.email,
                'role': admin.role.value,
                'tenant_id': admin.tenant_id,
                'is_principal_admin': True,
            },
        }, 201


@ns.route('/<int:tenant_id>')
class TenantResource(Resource):
    @jwt_required()
    def get(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouve'}, 404
        return tenant.to_dict(), 200

    @jwt_required()
    def put(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err
        tenant = db.session.get(Tenant, tenant_id)
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
                if statut in (StatutTenant.ACTIF, StatutTenant.EN_ESSAI):
                    tenant.is_active = True
                else:
                    tenant.is_active = False
        db.session.commit()
        try:
            broadcast_to_tenant(tenant.id, 'tenant:updated', tenant.to_dict())
        except Exception:
            pass
        return tenant.to_dict(), 200


@ns.route('/<int:tenant_id>/suspend')
class TenantSuspend(Resource):
    @jwt_required()
    def post(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouve'}, 404
        if tenant.statut == StatutTenant.BLOQUE:
            return {'message': 'Tenant déjà suspendu'}, 200
        tenant.statut = StatutTenant.BLOQUE
        db.session.commit()
        return {'message': 'Tenant suspendu', 'tenant': tenant.to_dict()}, 200


def _ensure_principal_admin():
    user_id = get_jwt_identity()
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    user = db.session.get(Utilisateur, user_id)
    if not user or not user.is_principal_admin:
        return {'message': 'Acces refuse : admin principal requis'}, 403
    tenant = db.session.get(Tenant, user.tenant_id)
    if not tenant or tenant.admin_principal_id != user.id:
        return {'message': 'Acces refuse : admin principal requis'}, 403
    return None


@ns.route('/me/employee-key')
class TenantEmployeeKey(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_principal_admin()
        if err:
            return err
        user_id = get_jwt_identity()
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)
        user = db.session.get(Utilisateur, user_id)
        if not user or not user.employee_key_hash:
            return {'message': 'Aucune cle employe generee'}, 404
        return {
            'has_employee_key': True,
            'status': user.employee_key_status,
        }, 200

    @jwt_required()
    def post(self):
        err = _ensure_principal_admin()
        if err:
            return err
        user_id = get_jwt_identity()
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)
        user = db.session.get(Utilisateur, user_id)
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404

        raw_key = secrets.token_urlsafe(32)
        user.employee_key_hash = bcrypt.hashpw(
            raw_key.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        user.employee_key_status = 'active'
        db.session.add(user)
        db.session.commit()

        return {
            'message': 'Cle employe regenerée avec succès',
            'employee_key': raw_key,
            'status': 'active',
        }, 200
