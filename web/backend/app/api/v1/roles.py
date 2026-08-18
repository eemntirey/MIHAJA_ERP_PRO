from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.role_permission import RoleModel, Permission, role_permissions
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app import db

ns = Namespace('roles', description='Gestion des roles et permissions')

_ALLOWED_FIELDS = {'name', 'display_name', 'description', 'is_default', 'is_system'}


def _ensure_admin():
    user_id = get_jwt_identity()
    user = Utilisateur.query.get(user_id)
    if not user:
        return {'message': 'Utilisateur non trouve'}, 401
    if not (user.is_super_admin or user.is_admin):
        return {'message': 'Acces administrateur requis'}, 403
    return None


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
        name = data.get('name')
        if not name:
            return {'message': 'Le nom du role est requis'}, 400
        existing = RoleModel.query.filter_by(name=name).first()
        if existing:
            return {'message': 'Un role avec ce nom existe deja'}, 409
        role = RoleModel(
            name=name,
            display_name=data.get('display_name', name),
            description=data.get('description'),
            is_default=_coerce_boolean(data.get('is_default'), default=False),
            is_system=_coerce_boolean(data.get('is_system'), default=False),
        )
        permission_ids = data.get('permission_ids') or []
        if isinstance(permission_ids, list):
            for pid in permission_ids:
                perm = Permission.query.get(pid)
                if perm:
                    role.permissions.append(perm)
        db.session.add(role)
        db.session.commit()
        return role.to_dict(), 201


@ns.route('/<int:role_id>')
class RoleResource(Resource):
    @jwt_required()
    def get(self, role_id):
        err = _ensure_admin()
        if err:
            return err
        role = RoleModel.query.get(role_id)
        if not role:
            return {'message': 'Role non trouve'}, 404
        return role.to_dict(), 200

    @jwt_required()
    def put(self, role_id):
        err = _ensure_admin()
        if err:
            return err
        role = RoleModel.query.get(role_id)
        if not role:
            return {'message': 'Role non trouve'}, 404
        data = request.get_json() or {}
        for key in _ALLOWED_FIELDS:
            if key in data:
                setattr(role, key, data[key])
        if 'permission_ids' in data:
            role.permissions = []
            for pid in data.get('permission_ids') or []:
                perm = Permission.query.get(pid)
                if perm:
                    role.permissions.append(perm)
        db.session.commit()
        return role.to_dict(), 200

    @jwt_required()
    def delete(self, role_id):
        err = _ensure_admin()
        if err:
            return err
        role = RoleModel.query.get(role_id)
        if not role:
            return {'message': 'Role non trouve'}, 404
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
        role = RoleModel.query.get(role_id)
        perm = Permission.query.get(permission_id)
        if not role or not perm:
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
        role = RoleModel.query.get(role_id)
        perm = Permission.query.get(permission_id)
        if not role or not perm:
            return {'message': 'Role ou permission introuvable'}, 404
        if perm in role.permissions:
            role.permissions.remove(perm)
            db.session.commit()
        return {'message': 'Permission retiree'}, 200
