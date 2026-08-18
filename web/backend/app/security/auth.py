from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from flask import request, g
from functools import wraps
from sqlalchemy import or_
from app.models.utilisateur import Utilisateur
from app.models.tenant import Tenant
from app import db
import bcrypt


def hash_password(password):
    """Hash un mot de passe avec bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password, password_hash):
    """Vérifie un mot de passe hashé"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def create_access_token_for_user(user):
    """Crée un token d'accès pour un utilisateur"""
    return create_access_token(
        identity=user.id,
        additional_claims={
            'username': user.username,
            'email': user.email,
            'role': user.role.value if hasattr(user.role, 'value') else user.role,
            'tenant_id': user.tenant_id,
        }
    )


def authenticate_user(identifier, password, tenant_slug=None):
    """Authentifie un utilisateur"""
    tenant = None
    
    if tenant_slug:
        tenant = Tenant.query.filter_by(slug=tenant_slug, is_active=True).first()
        if not tenant:
            return None, "Tenant non trouvé"
        user = Utilisateur.query.filter(
            Utilisateur.tenant_id == tenant.id,
            Utilisateur.is_active == True,
            or_(Utilisateur.username == identifier, Utilisateur.email == identifier)
        ).first()
    else:
        user = Utilisateur.query.filter(
            Utilisateur.is_active == True,
            or_(Utilisateur.username == identifier, Utilisateur.email == identifier)
        ).first()
        if user and user.tenant_id:
            tenant = Tenant.query.get(user.tenant_id)
    
    if not user:
        return None, "Utilisateur non trouvé"
    
    if not verify_password(password, user.password_hash):
        return None, "Mot de passe incorrect"
    
    g.current_tenant = tenant
    g.current_user = user
    
    # Générer les tokens
    access_token = create_access_token(
        identity=user.id,
        additional_claims={
            'username': user.username,
            'email': user.email,
            'role': user.role.value if hasattr(user.role, 'value') else user.role,
            'tenant_id': tenant.id if tenant else user.tenant_id,
            'tenant_slug': tenant.slug if tenant else None
        }
    )
    refresh_token = create_refresh_token(identity=user.id)
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(),
        'tenant': tenant.to_dict() if tenant else None
    }, None