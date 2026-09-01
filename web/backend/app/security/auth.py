from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from flask import request, g
from functools import wraps
from sqlalchemy import or_
from app.models.utilisateur import Utilisateur, StatutUtilisateur, StatutAdmin, Role
from app.models.tenant import Tenant, StatutTenant
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.admin_device import AdminDevice, StatutDevice
from app import db
import bcrypt
from datetime import datetime


def hash_password(password):
    """Hash un mot de passe avec bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password, password_hash):
    """Vérifie un mot de passe hashé"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def _validate_password(password):
    if not password or len(password) < 8:
        return 'Le mot de passe doit contenir au moins 8 caracteres'
    if not any(c.isalpha() for c in password):
        return 'Le mot de passe doit contenir au moins une lettre'
    if not any(c.isdigit() for c in password):
        return 'Le mot de passe doit contenir au moins un chiffre'
    return None


def _check_admin_device(user, device_id=None, tenant=None):
    """Vérifie les conditions d'accès lors d'une connexion professionnelle.

    Connexion par email + mot de passe. La vérification de l'appareil
    (uniquement pour le rôle ADMIN) garantit que l'admin utilise un appareil
    enregistré.

    Retourne (autorisé, message).
    """
    if not user or user.role == Role.SUPER_ADMIN:
        return True, None

    # Comptes hors tenant (ex: utilisateur simple sans entreprise) : pas de contrainte.
    if not tenant:
        return True, None

    if user.admin_statut is not None and user.admin_statut != StatutAdmin.ACTIVE:
        return False, 'Administrateur suspendu ou revoque'

    # Suivi de l'appareil (uniquement pour le rôle ADMIN). L'identifiant
    # d'appareil est optionnel : s'il est fourni, il est enregistré/mis à
    # jour ; dans le cas contraire la connexion n'est pas bloquée.
    if user.role == Role.ADMIN and device_id:
        device = AdminDevice.query.filter_by(
            user_id=user.id,
            device_id=device_id,
            statut=StatutDevice.ACTIVE
        ).first()
        if not device:
            any_device = AdminDevice.query.filter_by(user_id=user.id).first()
            if not any_device and device_id:
                device = AdminDevice(
                    user_id=user.id,
                    device_id=device_id,
                    device_name=None,
                    statut=StatutDevice.ACTIVE,
                    last_seen=datetime.utcnow()
                )
                db.session.add(device)
                user.device_id = device_id
                db.session.add(user)
                db.session.commit()
            else:
                return False, 'Appareil non autorise'
        else:
            device.last_seen = datetime.utcnow()
            db.session.add(device)
            db.session.commit()

    return True, None


def _check_subscription_for_admin(tenant):
    """Vérifie que le tenant a un abonnement actif pour les rôles ADMIN/MANAGER/etc.
    
    Retourne (autorisé, message).
    """
    if not tenant:
        return False, 'Aucun tenant associe'
    
    now = datetime.utcnow()
    abonnement_actif = Abonnement.query.filter(
        Abonnement.tenant_id == tenant.id,
        Abonnement.statut == StatutAbonnement.ACTIF,
        Abonnement.date_fin > now,
        Abonnement.is_active == True
    ).first()
    if not abonnement_actif:
        if tenant.statut.value == 'en_essai':
            return True, None
        return False, 'Abonnement requis'
    return True, None


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


def authenticate_user(identifier, password, tenant_slug=None, device_id=None):
    """Authentifie un utilisateur avec vérification multi-niveaux"""
    tenant = None
    
    if tenant_slug:
        tenant = Tenant.query.filter_by(slug=tenant_slug, is_active=True).first()
        if not tenant:
            return None, "Tenant non trouve"
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
            tenant = db.session.get(Tenant, user.tenant_id)
    
    if not user:
        return None, "Utilisateur non trouve"
    
    if not verify_password(password, user.password_hash):
        return None, "Mot de passe incorrect"
    
    if user.statut != StatutUtilisateur.ACTIF:
        return None, "Utilisateur inactif ou bloque"
    
    allowed, error_msg = _check_admin_device(
        user, device_id=device_id, tenant=tenant
    )
    if not allowed:
        return None, error_msg
    
    if tenant and user.role not in [Role.SUPER_ADMIN, Role.USER, Role.ACCOUNTANT]:
        if not tenant.is_active or tenant.statut in (StatutTenant.INACTIF, StatutTenant.BLOQUE):
            return None, "Tenant suspendu ou inactif"
        allowed, error_msg = _check_subscription_for_admin(tenant)
        if not allowed:
            return None, error_msg
    
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
        'tenant': tenant.to_dict() if tenant else None,
    }, None