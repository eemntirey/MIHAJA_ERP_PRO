from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.role_permission import RoleModel
from app import db
from app.security.auth import hash_password

ns = Namespace('users', description='Gestion des utilisateurs')

_ALLOWED_USER_FIELDS = {'username', 'email', 'nom', 'prenom', 'telephone', 'mobile', 'role', 'statut', 'custom_role_id'}


def _ensure_admin():
    user_id = get_jwt_identity()
    user = Utilisateur.query.get(user_id)
    if not user:
        return {'message': 'Utilisateur non trouve'}, 401
    if not (user.is_super_admin or user.is_admin):
        return {'message': 'Acces administrateur requis'}, 403
    return None


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
    @jwt_required()
    def get(self):
        err = _ensure_admin()
        if err:
            return err
        search = (request.args.get('search') or '').strip().lower()
        role_filter = (request.args.get('role') or '').strip().lower()
        statut_filter = (request.args.get('statut') or '').strip().lower()
        query = Utilisateur.query.filter_by(is_active=True)
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

    @jwt_required()
    def post(self):
        err = _ensure_admin()
        if err:
            return err
        data = request.get_json() or {}
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        if not username or not email or not password:
            return {'message': 'username, email et password requis'}, 400
        if Utilisateur.query.filter((Utilisateur.email == email) | (Utilisateur.username == username)).first():
            return {'message': 'Un utilisateur avec cet email ou username existe deja'}, 409
        user = Utilisateur(
            username=username,
            email=email,
            password_hash=hash_password(password),
            nom=data.get('nom'),
            prenom=data.get('prenom'),
            telephone=data.get('telephone'),
            mobile=data.get('mobile'),
            role=_coerce_role(data.get('role', 'user')),
            statut=_coerce_statut(data.get('statut')) or StatutUtilisateur.ACTIF,
            custom_role_id=data.get('custom_role_id'),
            tenant_id=data.get('tenant_id'),
        )
        db.session.add(user)
        db.session.commit()
        return user.to_dict(), 201


@ns.route('/<int:user_id>')
class UserResource(Resource):
    @jwt_required()
    def get(self, user_id):
        err = _ensure_admin()
        if err:
            return err
        user = Utilisateur.query.get(user_id)
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404
        return user.to_dict(), 200

    @jwt_required()
    def put(self, user_id):
        err = _ensure_admin()
        if err:
            return err
        user = Utilisateur.query.get(user_id)
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404
        data = request.get_json() or {}
        for key in _ALLOWED_USER_FIELDS:
            if key not in data:
                continue
            value = data[key]
            if key == 'role':
                value = _coerce_role(value)
            elif key == 'statut':
                value = _coerce_statut(value)
            setattr(user, key, value)
        if 'password' in data and data['password']:
            user.password_hash = hash_password(data['password'])
        db.session.commit()
        return user.to_dict(), 200

    @jwt_required()
    def delete(self, user_id):
        err = _ensure_admin()
        if err:
            return err
        user = Utilisateur.query.get(user_id)
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404
        if user.is_super_admin:
            return {'message': 'Impossible de supprimer un super administrateur'}, 400
        user.is_active = False
        db.session.commit()
        return {'message': 'Utilisateur desactive'}, 200
