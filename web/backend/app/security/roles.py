from functools import wraps
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask import jsonify
from app import db
from app.models.utilisateur import Utilisateur, Role
from app.models.role_permission import RoleModel


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


PERMISSIONS = {
    'super_admin': ['*'],
    'admin': ['*'],
    'manager': [
        'product.create', 'product.update', 'product.delete',
        'stock.view', 'stock.update',
        'sale.view', 'sale.create', 'sale.update',
        'user.view', 'user.create', 'user.update',
        'report.view'
    ],
    'sales': [
        'product.view',
        'sale.view', 'sale.create',
        'client.view', 'client.create', 'client.update',
        'quote.view', 'quote.create'
    ],
    'stock': [
        'product.view',
        'stock.view', 'stock.update',
        'supplier.view', 'supplier.create', 'supplier.update',
        'purchase_order.view', 'purchase_order.create'
    ],
    'accountant': [
        'product.view',
        'invoice.view', 'invoice.create', 'invoice.update',
        'payment.view', 'payment.create',
        'report.view'
    ],
    'user': [
        'product.view',
        'profile.view', 'profile.update'
    ]
}

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
        if not user or user.role not in [Role.ADMIN, Role.SUPER_ADMIN]:
            return jsonify({'message': 'Acces administrateur requis'}), 403
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        user = db.session.get(Utilisateur, user_id)
        if not user or user.role != Role.SUPER_ADMIN:
            return jsonify({'message': 'Acces super administrateur requis'}), 403
        return f(*args, **kwargs)
    return jwt_required()(decorated_function)
