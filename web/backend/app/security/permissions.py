from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from app.models.utilisateur import Utilisateur, Role
from .roles import has_permission, PERMISSIONS


def permission_required(permission):
    """Décorateur pour vérifier les permissions"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            user_id = get_jwt_identity()
            if not has_permission(user_id, permission):
                return jsonify({'message': 'Permission non accordée'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

