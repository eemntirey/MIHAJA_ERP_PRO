from flask import request, g
from flask_restx import Namespace, Resource
from flask_jwt_extended import get_jwt_identity
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.role_permission import RoleModel
from app.models.tenant import Tenant
from app import db
from app.security.auth import hash_password, _validate_password
from app.security.plan_limits import check_plan_limits, check_admin_limit, require_module
from app.security.tenant import tenant_required, get_current_tenant_id
from app.utils.audit import log_audit
from app.models.audit_log import TypeActionAudit

ns = Namespace('users', description='Gestion des utilisateurs')

_ALLOWED_USER_FIELDS = {'username', 'email', 'nom', 'prenom', 'telephone', 'mobile', 'role', 'statut', 'custom_role_id'}


def _require_admin():
    """Vérifie que l'utilisateur courant est admin ou super admin.

    Retourne (None, None) si autorisé, sinon (message, status).
    """
    user = getattr(g, 'current_user', None)
    if user is None:
        return {'message': 'Utilisateur non trouve'}, 401
    if not (user.is_super_admin or user.is_admin):
        return {'message': 'Acces administrateur requis'}, 403
    return None, None


def _is_global_admin():
    """True si l'utilisateur courant est super admin (accès global multi-tenant)."""
    user = getattr(g, 'current_user', None)
    return bool(user) and bool(user.is_super_admin)


def _get_tenant_scoped_user(user_id):
    """Récupère un utilisateur en respectant la portée tenant.

    Un admin de tenant ne peut manipuler que les utilisateurs de son propre tenant.
    """
    user = db.session.get(Utilisateur, user_id)
    if user is None:
        return None
    current_tenant_id = get_current_tenant_id()
    if current_tenant_id is not None and user.tenant_id != current_tenant_id:
        return None
    return user


def _coerce_statut(value):
    if value is None:
        return None
    if isinstance(value, StatutUtilisateur):
        return value
    normalized = str(value).strip().lower()
    for member in StatutUtilisateur:
        if member.value == normalized or member.name.lower() == normalized:
            return member
    return None


def _coerce_role(value):
    if value is None:
        return Role.USER
    if isinstance(value, Role):
        return value
    normalized = str(value).strip().lower()
    for member in Role:
        if member.value == normalized or member.name.lower() == normalized:
            return member
    return Role.USER


@ns.route('/')
class UserList(Resource):
    @tenant_required
    def get(self):
        err, status = _require_admin()
        if err:
            return err, status
        search = (request.args.get('search') or '').strip().lower()
        role_filter = (request.args.get('role') or '').strip().lower()
        statut_filter = (request.args.get('statut') or '').strip().lower()
        query = Utilisateur.query.filter_by(is_active=True)
        # Portée tenant : un admin de tenant ne voit que les utilisateurs de son tenant.
        current_tenant_id = get_current_tenant_id()
        if current_tenant_id is not None:
            query = query.filter(Utilisateur.tenant_id == current_tenant_id)
        if search:
            query = query.filter(
                db.or_(
                    Utilisateur.username.ilike(f'%{search}%'),
                    Utilisateur.email.ilike(f'%{search}%'),
                    Utilisateur.nom.ilike(f'%{search}%'),
                    Utilisateur.prenom.ilike(f'%{search}%'),
                )
            )
        if role_filter:
            coerced = _coerce_role(role_filter)
            query = query.filter(Utilisateur.role == coerced)
        if statut_filter:
            coerced = _coerce_statut(statut_filter)
            if coerced:
                query = query.filter(Utilisateur.statut == coerced)
        users = query.order_by(Utilisateur.created_at.desc()).all()
        return {'users': [u.to_dict() for u in users]}, 200

    @tenant_required
    @check_plan_limits('utilisateurs')
    @check_admin_limit()
    def post(self):
        err, status = _require_admin()
        if err:
            return err, status
        data = request.get_json() or {}
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        if not username or not email or not password:
            return {'message': 'username, email et password requis'}, 400
        pwd_error = _validate_password(password)
        if pwd_error:
            return {'message': pwd_error}, 400
        existing = (
            Utilisateur.query.execution_options(_skip_tenant_filter=True)
            .filter((Utilisateur.email == email) | (Utilisateur.username == username))
            .first()
        )
        if existing:
            return {'message': 'Un utilisateur avec cet email ou username existe deja'}, 409
        role = _coerce_role(data.get('role', 'user'))
        if role == Role.SUPER_ADMIN and not _is_global_admin():
            return {'message': 'Seul un super administrateur peut creer un compte super_admin'}, 403
        tenant_id = data.get('tenant_id')
        current_tenant_id = get_current_tenant_id()
        if current_tenant_id is not None:
            if tenant_id is not None and tenant_id != current_tenant_id:
                return {'message': 'Vous ne pouvez pas creer d\'utilisateur dans un autre tenant'}, 403
            tenant_id = current_tenant_id
        if tenant_id is not None:
            tenant = db.session.get(Tenant, tenant_id)
            if not tenant:
                return {'message': 'Tenant introuvable'}, 404
        creator_id = get_jwt_identity()
        user = Utilisateur(
            username=username,
            email=email,
            password_hash=hash_password(password),
            nom=data.get('nom'),
            prenom=data.get('prenom'),
            telephone=data.get('telephone'),
            mobile=data.get('mobile'),
            role=role,
            statut=_coerce_statut(data.get('statut')) or StatutUtilisateur.ACTIF,
            custom_role_id=data.get('custom_role_id'),
            tenant_id=tenant_id,
            created_by=creator_id,
        )
        db.session.add(user)
        db.session.commit()
        try:
            log_audit(
                TypeActionAudit.CREATION_UTILISATEUR,
                f"Création de l'utilisateur {user.username} (role={role.value})",
                tenant_id=tenant_id,
                utilisateur_id=get_jwt_identity(),
                metadata={'user_id': user.id, 'role': role.value},
            )
        except Exception:
            pass
        return user.to_dict(), 201


@ns.route('/<int:user_id>')
class UserResource(Resource):
    @tenant_required
    def get(self, user_id):
        err, status = _require_admin()
        if err:
            return err, status
        user = _get_tenant_scoped_user(user_id)
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404
        return user.to_dict(), 200

    @tenant_required
    def put(self, user_id):
        err, status = _require_admin()
        if err:
            return err, status
        user = _get_tenant_scoped_user(user_id)
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404
        if user.is_super_admin and not _is_global_admin():
            return {'message': 'Seul un super administrateur peut modifier un compte super_admin'}, 403
        data = request.get_json() or {}
        old_role = user.role
        for key in _ALLOWED_USER_FIELDS:
            if key not in data:
                continue
            value = data[key]
            if key == 'role':
                coerced = _coerce_role(value)
                if coerced == Role.SUPER_ADMIN and not _is_global_admin():
                    return {'message': 'Seul un super administrateur peut assigner le role super_admin'}, 403
                if coerced in (Role.ADMIN, Role.SUPER_ADMIN) and user.tenant_id:
                    tenant = db.session.get(Tenant, user.tenant_id)
                    if tenant and not check_admin_limit(tenant):
                        return {'message': 'Limite d\'administrateurs atteinte pour votre abonnement actuel.'}, 403
                value = coerced
            elif key == 'statut':
                value = _coerce_statut(value)
            setattr(user, key, value)
        if 'password' in data and data['password']:
            pwd_error = _validate_password(data['password'])
            if pwd_error:
                return {'message': pwd_error}, 400
            user.password_hash = hash_password(data['password'])
        user.updated_by = get_jwt_identity()
        db.session.commit()
        if old_role != user.role:
            log_audit(
                TypeActionAudit.CHANGEMENT_ROLE,
                f"Changement de rôle pour {user.username}: {old_role.value} -> {user.role.value}",
                tenant_id=user.tenant_id,
                utilisateur_id=g.current_user.id if hasattr(g, 'current_user') and g.current_user else None,
                metadata={'user_id': user.id, 'old_role': old_role.value, 'new_role': user.role.value},
            )
        return user.to_dict(), 200

    @tenant_required
    def delete(self, user_id):
        err, status = _require_admin()
        if err:
            return err, status
        user = _get_tenant_scoped_user(user_id)
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404
        if user.is_super_admin:
            return {'message': 'Impossible de supprimer un super administrateur'}, 400
        user.is_active = False
        db.session.commit()
        return {'message': 'Utilisateur desactive'}, 200
