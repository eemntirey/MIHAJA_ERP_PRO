from flask import request, g
from flask_restx import Namespace, Resource
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import IntegrityError
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.role_permission import RoleModel
from app.models.tenant import Tenant
from app.models.admin_device import AdminDevice
from app import db
from app.security.auth import hash_password, _validate_password, verify_password as _verify_password
from app.security.plan_limits import check_plan_limits, check_admin_limit, require_module, is_admin_limit_reached, is_employee_limit_reached, is_unlimited, _get_limits
from app.security.tenant import tenant_required, get_current_tenant_id
from app.security.roles import can_manage_role
from app.utils.audit import log_audit
from app.models.audit_log import TypeActionAudit
from app.websockets.socket_events import broadcast_to_tenant, broadcast_to_user

ns = Namespace('users', description='Gestion des utilisateurs')

_ALLOWED_USER_FIELDS = {'username', 'email', 'nom', 'prenom', 'telephone', 'mobile', 'role', 'statut', 'custom_role_id'}


def _require_admin():
    """Vérifie que l'utilisateur courant peut gérer les utilisateurs.

    Autorise SUPER_ADMIN (accès global), ADMIN du tenant, ou tout rôle
    disposant de la permission 'user.create'. Retourne (None, None) si
    autorisé, sinon (message, status).
    """
    user = getattr(g, 'current_user', None)
    if user is None:
        return {'message': 'Utilisateur non trouve'}, 401
    if user.is_super_admin or user.is_admin:
        return None, None
    if user.has_permission('user.create'):
        return None, None
    return {'message': 'Acces administrateur requis'}, 403


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


def _validate_custom_role(custom_role_id, tenant_id):
    if custom_role_id is None:
        return None, None
    role = db.session.get(RoleModel, custom_role_id)
    if not role:
        return {'message': 'Role personnalise introuvable'}, 404
    # Le rôle SUPER_ADMIN est protégé : un tenant ne peut pas l'assigner
    # en tant que rôle custom à un utilisateur (même si le role système est
    # identifié uniquement par son id). Un super administrateur peut.
    if not _is_global_admin() and (role.name or '').strip().lower() == Role.SUPER_ADMIN.value:
        return {'message': 'Ce role est reserve au super administrateur'}, 403
    if tenant_id is not None and role.tenant_id is not None and role.tenant_id != tenant_id:
        return {'message': 'Ce role personnalise n\'appartient pas a ce tenant'}, 403
    return None, None


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
        query = query.filter(Utilisateur.statut == StatutUtilisateur.ACTIF)
        current_tenant_id = get_current_tenant_id()
        if current_tenant_id is not None:
            query = query.filter(Utilisateur.tenant_id == current_tenant_id)
            query = query.filter(
                Utilisateur.role.in_([
                    Role.USER, Role.SALES, Role.STOCK, Role.ACCOUNTANT, Role.RH, Role.MANAGER
                ])
            )
        else:
            # Pas de tenant_id (super_admin plateforme) : on n'affiche que
            # les comptes administratifs (admin / super_admin) pour eviter
            # d'exposer l'ensemble des employes de tous les tenants.
            query = query.filter(
                Utilisateur.role.in_([Role.ADMIN, Role.SUPER_ADMIN])
            )
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
            .filter(
                Utilisateur.is_active == True,
                (Utilisateur.email == email) | (Utilisateur.username == username),
            )
            .first()
        )
        if existing:
            return {'message': 'Un utilisateur avec cet email ou username existe deja'}, 409
        role = _coerce_role(data.get('role', 'user'))
        if role == Role.SUPER_ADMIN and not _is_global_admin():
            return {'message': 'Seul un super administrateur peut creer un compte super_admin'}, 403
        if not _is_global_admin() and not can_manage_role(g.current_user.role, role):
            return {'message': 'Vous ne pouvez pas creer un utilisateur avec un role superieur ou egal au votre'}, 403
        if role == Role.ADMIN and not _is_global_admin():
            tenant_id = get_current_tenant_id()
            if tenant_id:
                tenant = db.session.get(Tenant, tenant_id)
                if tenant and is_admin_limit_reached(tenant):
                    return {'message': 'Limite d\'administrateurs atteinte pour votre abonnement actuel.'}, 403
        if role in (Role.USER, Role.SALES, Role.STOCK, Role.ACCOUNTANT, Role.RH, Role.MANAGER) and not _is_global_admin():
            tenant_id = get_current_tenant_id()
            if tenant_id:
                tenant = db.session.get(Tenant, tenant_id)
                if tenant and is_employee_limit_reached(tenant):
                    return {'message': 'Limite d\'employés atteinte pour votre abonnement actuel.'}, 403
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
        custom_role_id = data.get('custom_role_id')
        if custom_role_id in (None, ''):
            custom_role_id = None
        if custom_role_id is not None:
            err, status = _validate_custom_role(custom_role_id, tenant_id)
            if err:
                return err, status
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
            custom_role_id=custom_role_id,
            tenant_id=tenant_id,
            created_by=creator_id,
        )
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {'message': 'Un utilisateur avec cet email ou username existe deja'}, 409
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
        try:
            broadcast_to_tenant(tenant_id, 'user:updated', user.to_dict())
            broadcast_to_user(user.id, 'user:updated', user.to_dict())
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
                    if tenant and is_admin_limit_reached(tenant):
                        return {'message': 'Limite d\'administrateurs atteinte pour votre abonnement actuel.'}, 403
                if coerced in (Role.USER, Role.SALES, Role.STOCK, Role.ACCOUNTANT, Role.RH, Role.MANAGER) and user.tenant_id:
                    tenant = db.session.get(Tenant, user.tenant_id)
                    if tenant:
                        current_employees = Utilisateur.query.filter(
                            Utilisateur.tenant_id == user.tenant_id,
                            Utilisateur.role.in_([Role.USER, Role.SALES, Role.STOCK, Role.ACCOUNTANT, Role.RH, Role.MANAGER]),
                            Utilisateur.is_active == True,
                            Utilisateur.id != user.id,
                        ).count()
                        limits = _get_limits(tenant)
                        employee_limit = limits.get('max_employees')
                        if not is_unlimited(employee_limit) and current_employees >= employee_limit:
                            return {'message': 'Limite d\'employés atteinte pour votre abonnement actuel.'}, 403
                if not _is_global_admin() and not can_manage_role(g.current_user.role, coerced):
                    return {'message': 'Vous ne pouvez pas assigner un role superieur ou egal au votre'}, 403
                value = coerced
            elif key == 'statut':
                value = _coerce_statut(value)
            elif key == 'custom_role_id':
                if value in (None, ''):
                    value = None
                if value is not None:
                    err, status = _validate_custom_role(value, user.tenant_id)
                    if err:
                        return err, status
            setattr(user, key, value)
        if 'password' in data and data['password']:
            # Vérification de l'ancien mot de passe : un admin qui modifie le
            # mot de passe d'un autre utilisateur doit fournir le mot de passe
            # courant. Un utilisateur qui modifie son propre mot de passe peut
            # passer par le endpoint dédié /auth/change-password.
            if user.id != get_jwt_identity():
                current_pwd = data.get('current_password')
                if not current_pwd:
                    return {'message': 'Mot de passe actuel requis pour modifier celui d\'un autre utilisateur'}, 400
                if not _verify_password(user, current_pwd):
                    return {'message': 'Mot de passe actuel invalide'}, 403
            pwd_error = _validate_password(data['password'])
            if pwd_error:
                return {'message': pwd_error}, 400
            user.password_hash = hash_password(data['password'])
        user.updated_by = get_jwt_identity()
        db.session.commit()
        db.session.refresh(user)
        if old_role != user.role:
            log_audit(
                TypeActionAudit.CHANGEMENT_ROLE,
                f"Changement de rôle pour {user.username}: {old_role.value} -> {user.role.value}",
                tenant_id=user.tenant_id,
                utilisateur_id=g.current_user.id if hasattr(g, 'current_user') and g.current_user else None,
                metadata={'user_id': user.id, 'old_role': old_role.value, 'new_role': user.role.value},
            )
        try:
            broadcast_to_tenant(user.tenant_id, 'user:updated', user.to_dict())
            broadcast_to_user(user.id, 'user:updated', user.to_dict())
        except Exception:
            pass
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
        
        AdminDevice.query.filter_by(user_id=user.id).update(
            {AdminDevice.is_active: False}, synchronize_session=False
        )
        
        if user.tenant_id:
            tenant = db.session.get(Tenant, user.tenant_id)
            if tenant and tenant.admin_principal_id == user.id:
                tenant.admin_principal_id = None
                db.session.add(tenant)
        
        user.mark_deleted()
        db.session.commit()
        
        try:
            log_audit(
                TypeActionAudit.SUPPRESSION_UTILISATEUR,
                f"Suppression de l'utilisateur {user.username} (role={user.role.value})",
                tenant_id=user.tenant_id,
                utilisateur_id=get_jwt_identity(),
                metadata={'user_id': user.id, 'role': user.role.value},
            )
        except Exception:
            pass
        
        try:
            broadcast_to_tenant(user.tenant_id, 'user:updated', user.to_dict())
        except Exception:
            pass
        return {'message': 'Utilisateur supprime'}, 200
