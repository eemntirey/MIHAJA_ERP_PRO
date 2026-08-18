from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.role_permission import Permission
from app.models.utilisateur import Utilisateur
from app import db

ns = Namespace('permissions', description='Gestion des permissions')

_ALLOWED_FIELDS = {'code', 'description', 'module', 'action'}


def _ensure_admin():
    user_id = get_jwt_identity()
    user = Utilisateur.query.get(user_id)
    if not user:
        return {'message': 'Utilisateur non trouve'}, 401
    if not (user.is_super_admin or user.is_admin):
        return {'message': 'Acces administrateur requis'}, 403
    return None


@ns.route('/')
class PermissionList(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_admin()
        if err:
            return err
        search = (request.args.get('search') or '').strip().lower()
        module = (request.args.get('module') or '').strip().lower()
        query = Permission.query
        if search:
            query = query.filter(
                db.or_(
                    Permission.code.ilike(f'%{search}%'),
                    Permission.description.ilike(f'%{search}%'),
                )
            )
        if module:
            query = query.filter(Permission.module.ilike(f'%{module}%'))
        permissions = query.order_by(Permission.module.asc(), Permission.code.asc()).all()
        return {'permissions': [p.to_dict() for p in permissions]}, 200

    @jwt_required()
    def post(self):
        err = _ensure_admin()
        if err:
            return err
        data = request.get_json() or {}
        code = data.get('code')
        if not code:
            return {'message': 'Le code de permission est requis'}, 400
        existing = Permission.query.filter_by(code=code).first()
        if existing:
            return {'message': 'Une permission avec ce code existe deja'}, 409
        permission = Permission(
            code=code,
            description=data.get('description'),
            module=data.get('module'),
            action=data.get('action'),
        )
        db.session.add(permission)
        db.session.commit()
        return permission.to_dict(), 201


@ns.route('/<int:permission_id>')
class PermissionResource(Resource):
    @jwt_required()
    def get(self, permission_id):
        err = _ensure_admin()
        if err:
            return err
        permission = Permission.query.get(permission_id)
        if not permission:
            return {'message': 'Permission non trouvee'}, 404
        return permission.to_dict(), 200

    @jwt_required()
    def put(self, permission_id):
        err = _ensure_admin()
        if err:
            return err
        permission = Permission.query.get(permission_id)
        if not permission:
            return {'message': 'Permission non trouvee'}, 404
        data = request.get_json() or {}
        for key in _ALLOWED_FIELDS:
            if key in data:
                setattr(permission, key, data[key])
        db.session.commit()
        return permission.to_dict(), 200

    @jwt_required()
    def delete(self, permission_id):
        err = _ensure_admin()
        if err:
            return err
        permission = Permission.query.get(permission_id)
        if not permission:
            return {'message': 'Permission non trouvee'}, 404
        db.session.delete(permission)
        db.session.commit()
        return {'message': 'Permission supprimee'}, 200
