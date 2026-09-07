from functools import wraps
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask import jsonify
from app import db
from app.models.utilisateur import Utilisateur, Role
from app.models.role_permission import RoleModel


ROLE_HIERARCHY = {
    Role.SUPER_ADMIN: 100,
    Role.ADMIN: 80,
    Role.MANAGER: 60,
    Role.SALES: 40,
    Role.STOCK: 40,
    Role.ACCOUNTANT: 40,
    Role.RH: 40,
    Role.LIVREUR: 30,
    Role.USER: 20,
}


def get_role_level(role_value):
    normalized = normalize_role(role_value)
    if normalized is None:
        return 0
    return ROLE_HIERARCHY.get(normalized, 0)


def can_manage_role(creator_role, target_role):
    creator_level = get_role_level(creator_role)
    target_level = get_role_level(target_role)
    if target_role == Role.SUPER_ADMIN:
        return creator_level >= get_role_level(Role.SUPER_ADMIN)
    return creator_level >= target_level


def normalize_role(role_value):
    """Normalize role value for case-insensitive comparison.
    
    Args:
        role_value: Can be Role enum, string value (e.g., 'super_admin'), or string name (e.g., 'SUPER_ADMIN')
    
    Returns:
        Role enum value if valid, None otherwise
    """
    if role_value is None:
        return None
    
    if isinstance(role_value, Role):
        return role_value
    
    if isinstance(role_value, str):
        # Try to match by value (e.g., 'super_admin')
        for role in Role:
            if role.value.lower() == role_value.lower():
                return role
        # Try to match by name (e.g., 'SUPER_ADMIN')
        for role in Role:
            if role.name.lower() == role_value.lower():
                return role
    
    return None


def is_super_admin(role_value):
    """Check if role is SUPER_ADMIN (case-insensitive)."""
    normalized = normalize_role(role_value)
    return normalized == Role.SUPER_ADMIN


def is_admin(role_value):
    """Check if role is ADMIN or SUPER_ADMIN (case-insensitive)."""
    normalized = normalize_role(role_value)
    return normalized in (Role.ADMIN, Role.SUPER_ADMIN)


def is_manager(role_value):
    """Check if role is MANAGER, ADMIN, or SUPER_ADMIN (case-insensitive)."""
    normalized = normalize_role(role_value)
    return normalized in (Role.MANAGER, Role.ADMIN, Role.SUPER_ADMIN)


def has_role(role_value, *allowed_roles):
    """Check if role matches any of the allowed roles (case-insensitive)."""
    normalized = normalize_role(role_value)
    allowed_normalized = {normalize_role(r) for r in allowed_roles if normalize_role(r)}
    return normalized in allowed_normalized


from app.security.permission_matrix import ROLE_PERMISSIONS

PERMISSIONS = ROLE_PERMISSIONS


def has_permission(user_id, permission):
    user = db.session.get(Utilisateur, user_id)
    if not user:
        return False
    
    if user.custom_role_id and user.custom_role and user.custom_role.permissions:
        user_permissions = [p.code for p in user.custom_role.permissions]
        if '*' in user_permissions:
            return True
        return permission in user_permissions
    
    role = user.role.value if hasattr(user.role, 'value') else user.role
    user_permissions = PERMISSIONS.get(role, [])
    
    if '*' in user_permissions:
        return True
    return permission in user_permissions

def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        user = db.session.get(Utilisateur, user_id)
        if not user or not is_super_admin(user.role) and not is_admin(user.role):
            return jsonify({'message': 'Acces administrateur requis'}), 403
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        user = db.session.get(Utilisateur, user_id)
        if not user or not is_super_admin(user.role):
            return jsonify({'message': 'Acces super administrateur requis'}), 403
        return f(*args, **kwargs)
    return jwt_required()(decorated_function)
