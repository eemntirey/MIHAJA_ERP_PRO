from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.role_permission import RoleModel, Permission, role_permissions
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app import db
from sqlalchemy.exc import IntegrityError
from app.security.roles import is_super_admin
from app.security.tenant import get_current_tenant_id

ns = Namespace('roles', description='Gestion des roles et permissions')

_ALLOWED_FIELDS = {'name', 'display_name', 'description', 'is_default', 'is_system'}

# Nom canonique (enum) du rôle plateforme SUPER_ADMIN.
# Ce rôle est protégé : il doit JAMAIS être exposé aux tenants tant que
# l'utilisateur courant n'est pas lui-même SUPER_ADMIN. Le rôle reste présent
# en base de données (on ne le supprime pas) ; on le masque uniquement à la
# couche d'accès (API + UI) afin qu'un tenant ne puisse ni le voir, ni le
# créer/modifier, ni l'assigner.
SUPER_ADMIN_ROLE_NAME = Role.SUPER_ADMIN.value


def _current_user_is_super_admin():
    """True si l'utilisateur authentifié est un SUPER_ADMIN (rôle réel JWT/DB)."""
    user = _current_user()
    if user is None:
        return False
    return is_super_admin(user.role)


def _is_super_admin_role(role_model):
    """True si le RoleModel fourni est le rôle SUPER_ADMIN protégé (insensible à la casse)."""
    if role_model is None:
        return False
    return (role_model.name or '').strip().lower() == SUPER_ADMIN_ROLE_NAME


def _current_user():
    user_id = get_jwt_identity()
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    return db.session.get(Utilisateur, user_id)


def _ensure_admin():
    user = _current_user()
    if not user:
        return {'message': 'Utilisateur non trouve'}, 401
    if not (user.is_super_admin or user.is_admin):
        return {'message': 'Acces administrateur requis'}, 403
    return None


def _role_scope_filter():
    """Retourne le filtre de portée applicable aux rôles selon l'utilisateur courant.

    Source de vérité unique : tout code qui décide si un rôle "existe" ou
    "doit être affiché" pour un utilisateur doit passer par ce filtre.

    Règles :
      - super_admin  : aucun filtre (voit tous les rôles).
      - autres       : rôles du tenant courant OU rôles système (tenant_id IS NULL),
        à l'exclusion du rôle SUPER_ADMIN qui reste masqué aux tenants.
    """
    user = _current_user()
    if user and is_super_admin(user.role):
        return None
    tenant_id = get_current_tenant_id()
    if tenant_id is None and user and user.tenant_id:
        tenant_id = user.tenant_id
    conditions = [RoleModel.tenant_id.is_(None)]
    if tenant_id is not None:
        conditions.append(RoleModel.tenant_id == tenant_id)
    scope = db.or_(*conditions)
    # Masquer le rôle SUPER_ADMIN aux utilisateurs non super_admin.
    scope = db.and_(scope, db.func.lower(RoleModel.name) != SUPER_ADMIN_ROLE_NAME)
    return scope


def _tenant_scoped_query_for_roles(query):
    """Filtre le query selon la portee de l'utilisateur (voir _role_scope_filter).

    Bypass explicite de l'event listener SQLAlchemy global de filtrage tenant
    (app.security.tenant.register_tenant_filter_event) : ce listener ajoute
    inconditionnellement `entity.tenant_id == current_tenant_id` aux requetes
    ORM, ce qui ferait disparaitre les roles systeme (tenant_id IS NULL) de
    la liste et empecherait la verification d'existence de les detecter.

    Le scope des roles (incluant les roles systeme) est defini ici de maniere
    explicite et fait foi (cf. _role_scope_filter).
    """
    query = query.execution_options(_skip_tenant_filter=True)
    scope = _role_scope_filter()
    if scope is not None:
        query = query.filter(scope)
    return query


def _get_role_by_id(role_id):
    """Charge un role par id sans appliquer le filtre tenant global, pour que
    les roles systeme (tenant_id IS NULL) restent accessibles. Le filtrage
    multi-tenant est ensuite verifie explicitement en Python."""
    return db.session.get(
        RoleModel, role_id, execution_options={'_skip_tenant_filter': True}
    )


def _coerce_boolean(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('1', 'true', 'yes', 'on')


@ns.route('/')
class RoleList(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_admin()
        if err:
            return err
        search = (request.args.get('search') or '').strip().lower()
        query = RoleModel.query
        query = _tenant_scoped_query_for_roles(query)
        if search:
            query = query.filter(
                db.or_(
                    RoleModel.name.ilike(f'%{search}%'),
                    RoleModel.display_name.ilike(f'%{search}%'),
                )
            )
        roles = query.order_by(RoleModel.name.asc()).all()
        return {'roles': [r.to_dict() for r in roles]}, 200

    @jwt_required()
    def post(self):
        err = _ensure_admin()
        if err:
            return err
        data = request.get_json() or {}
        raw_name = data.get('name')
        if not raw_name:
            return {'message': 'Le nom du role est requis'}, 400
        name = raw_name.strip().lower()
        if name == SUPER_ADMIN_ROLE_NAME and not _current_user_is_super_admin():
            return {'message': 'Ce role est reserve au super administrateur'}, 403
        tenant_id = get_current_tenant_id()
        if tenant_id is None:
            user = _current_user()
            if user and user.tenant_id:
                tenant_id = user.tenant_id
            else:
                tenant_id = None
        existing_query = RoleModel.query.filter(
            db.func.lower(RoleModel.name) == name
        )
        existing_query = _tenant_scoped_query_for_roles(existing_query)
        if existing_query.first():
            return {'message': 'Un role avec ce nom existe deja'}, 409
        role = RoleModel(
            name=name,
            display_name=data.get('display_name') or name,
            description=data.get('description'),
            is_default=_coerce_boolean(data.get('is_default'), default=False),
            is_system=_coerce_boolean(data.get('is_system'), default=False),
            tenant_id=tenant_id,
        )
        permission_ids = data.get('permission_ids') or []
        if isinstance(permission_ids, list):
            for pid in permission_ids:
                perm = db.session.get(Permission, pid)
                if perm:
                    role.permissions.append(perm)
        db.session.add(role)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {'message': 'Un role avec ce nom existe deja'}, 409
        return role.to_dict(), 201


@ns.route('/<int:role_id>')
class RoleResource(Resource):
    @jwt_required()
    def get(self, role_id):
        err = _ensure_admin()
        if err:
            return err
        role = _get_role_by_id(role_id)
        if not role:
            return {'message': 'Role non trouve'}, 404
        user = _current_user()
        if not is_super_admin(user.role) and _is_super_admin_role(role):
            return {'message': 'Role non trouve'}, 404
        if not is_super_admin(user.role) and role.tenant_id is not None and role.tenant_id != user.tenant_id:
            return {'message': 'Role introuvable'}, 404
        return role.to_dict(), 200

    @jwt_required()
    def put(self, role_id):
        err = _ensure_admin()
        if err:
            return err
        role = _get_role_by_id(role_id)
        if not role:
            return {'message': 'Role non trouve'}, 404
        user = _current_user()
        if not is_super_admin(user.role) and _is_super_admin_role(role):
            return {'message': 'Role non trouve'}, 404
        if not is_super_admin(user.role) and role.tenant_id is not None and role.tenant_id != user.tenant_id:
            return {'message': 'Role introuvable'}, 404
        data = request.get_json() or {}
        if 'name' in data:
            new_name = (data.get('name') or '').strip().lower()
            if new_name == SUPER_ADMIN_ROLE_NAME and not _current_user_is_super_admin():
                return {'message': 'Ce role est reserve au super administrateur'}, 403
            data['name'] = new_name
        for key in _ALLOWED_FIELDS:
            if key in data:
                setattr(role, key, data[key])
        if 'permission_ids' in data:
            role.permissions = []
            for pid in data.get('permission_ids') or []:
                perm = db.session.get(Permission, pid)
                if perm:
                    role.permissions.append(perm)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {'message': 'Un role avec ce nom existe deja'}, 409
        return role.to_dict(), 200

    @jwt_required()
    def delete(self, role_id):
        err = _ensure_admin()
        if err:
            return err
        role = _get_role_by_id(role_id)
        if not role:
            return {'message': 'Role non trouve'}, 404
        user = _current_user()
        if not is_super_admin(user.role) and _is_super_admin_role(role):
            return {'message': 'Role non trouve'}, 404
        if not is_super_admin(user.role) and role.tenant_id is not None and role.tenant_id != user.tenant_id:
            return {'message': 'Role introuvable'}, 404
        if role.is_system:
            return {'message': 'Impossible de supprimer un role systeme'}, 400
        db.session.delete(role)
        db.session.commit()
        return {'message': 'Role supprime'}, 200


@ns.route('/permissions')
class RolePermissionList(Resource):
    @jwt_required()
    def post(self):
        err = _ensure_admin()
        if err:
            return err
        data = request.get_json() or {}
        role_id = data.get('role_id')
        permission_id = data.get('permission_id')
        if not role_id or not permission_id:
            return {'message': 'role_id et permission_id requis'}, 400
        role = _get_role_by_id(role_id)
        perm = db.session.get(Permission, permission_id)
        if not role or not perm:
            return {'message': 'Role ou permission introuvable'}, 404
        user = _current_user()
        if not is_super_admin(user.role) and _is_super_admin_role(role):
            return {'message': 'Role ou permission introuvable'}, 404
        if not is_super_admin(user.role) and role.tenant_id is not None and role.tenant_id != user.tenant_id:
            return {'message': 'Role ou permission introuvable'}, 404
        if perm in role.permissions:
            return {'message': 'Permission deja assignee'}, 409
        role.permissions.append(perm)
        db.session.commit()
        return {'message': 'Permission ajoutee'}, 201


@ns.route('/permissions/<int:role_id>/<int:permission_id>')
class RolePermissionResource(Resource):
    @jwt_required()
    def delete(self, role_id, permission_id):
        err = _ensure_admin()
        if err:
            return err
        role = _get_role_by_id(role_id)
        perm = db.session.get(Permission, permission_id)
        if not role or not perm:
            return {'message': 'Role ou permission introuvable'}, 404
        user = _current_user()
        if not is_super_admin(user.role) and _is_super_admin_role(role):
            return {'message': 'Role ou permission introuvable'}, 404
        if not is_super_admin(user.role) and role.tenant_id is not None and role.tenant_id != user.tenant_id:
            return {'message': 'Role ou permission introuvable'}, 404
        if perm in role.permissions:
            role.permissions.remove(perm)
            db.session.commit()
        return {'message': 'Permission retiree'}, 200


@ns.route('/presets')
class RolePresetList(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_admin()
        if err:
            return err
        from app.security.permission_matrix import ROLE_PERMISSIONS
        hide_super_admin = not _current_user_is_super_admin()
        presets = []
        for name, perms in ROLE_PERMISSIONS.items():
            if name == 'support':
                continue
            if hide_super_admin and name == SUPER_ADMIN_ROLE_NAME:
                continue
            preset_perms = [p for p in perms if p != '*']
            perm_objects = Permission.query.filter(Permission.code.in_(preset_perms)).all() if preset_perms else []
            perm_ids = [p.id for p in perm_objects]
            perm_map = {p.code: p.id for p in perm_objects}
            presets.append({
                'name': name,
                'display_name': name.replace('_', ' ').title(),
                'permission_codes': preset_perms,
                'permission_ids': perm_ids,
                'permission_map': perm_map,
            })
        return {'presets': presets}, 200
