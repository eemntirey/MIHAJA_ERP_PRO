# -*- coding: utf-8 -*-
# app/security/auth.py

from flask import current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt, verify_jwt_in_request,
)
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


# ============================================================
# HACHAGE ET VERIFICATION
# ============================================================

def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password, password_hash):
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _validate_password(password):
    """Delegue a la politique centralisee (app.security.password_policy)."""
    from app.security.password_policy import validate_password_strength
    return validate_password_strength(password)


# ============================================================
# INVALIDATION DE SESSIONS
# ============================================================

def invalidate_user_tokens(user):
    """Incremente la version de token d un utilisateur.

    Lors d un changement de mot de passe, cette fonction est appelee
    pour incrementer token_version. Tous les JWT emis avant ce
    changement portent une valeur pwd_v plus ancienne et sont
    consideres comme inavlides par require_password_changed.
    """
    user.token_version = (user.token_version or 0) + 1
    db.session.add(user)
    db.session.commit()


# ============================================================
# GARDE DE SECURITE : PREMIERE CONNEXION
# ============================================================

def require_password_changed(fn):
    """Decoreur qui bloque l acces a un endpoint si must_change_password est True.

    Les endpoints /auth/first-login-change et /auth/change-password sont
    exempts de ce guard pour permettre a l utilisateur de changer son
    mot de passe (premiere connexion ou changement normal).
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from flask_jwt_extended.exceptions import (
            NoAuthorizationError, InvalidHeaderError,
            RevokedTokenError, JWTDecodeError
        )
        try:
            verify_jwt_in_request()
        except NoAuthorizationError:
            return {"message": "En-tete Authorization manquant ou invalide"}, 401
        except InvalidHeaderError:
            return {"message": "En-tete Authorization invalide"}, 401
        except RevokedTokenError:
            return {"message": "Token JWT revoque"}, 401
        except JWTDecodeError:
            return {"message": "Token JWT invalide"}, 401
        except Exception:
            return {"message": "Token JWT invalide ou expire"}, 401

        user_id = get_jwt_identity()
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)

        user = db.session.get(Utilisateur, user_id)
        if not user:
            return {"message": "Utilisateur introuvable"}, 404

        if user.must_change_password:
            return {
                "message": "Vous devez d abord modifier votre mot de passe temporaire",
                "code": "PASSWORD_CHANGE_REQUIRED",
            }, 403

        # Verifie la version du token (invalidite apres changement de mdp)
        claims = get_jwt() or {}
        token_pwd_v = claims.get("pwd_v", 0)
        if token_pwd_v < (user.token_version or 0):
            return {
                "message": "Votre session a expire. Veuillez vous reconnecter.",
                "code": "TOKEN_VERSION_EXPIRED",
            }, 401

        return fn(*args, **kwargs)
    return wrapper


# ============================================================
# VERIFICATION APPAREIL (ADMIN)
# ============================================================

def _check_admin_device(user, device_id=None, tenant=None):
    if not user or user.role == Role.SUPER_ADMIN:
        return True, None
    if not tenant:
        return True, None
    if user.admin_statut is not None and user.admin_statut != StatutAdmin.ACTIVE:
        return False, "Administrateur suspendu ou revoque"
    if user.role == Role.ADMIN and device_id:
        device = AdminDevice.query.filter_by(
            user_id=user.id, device_id=device_id, statut=StatutDevice.ACTIVE
        ).first()
        if not device:
            any_device = AdminDevice.query.filter_by(user_id=user.id).first()
            if not any_device and device_id:
                device = AdminDevice(
                    user_id=user.id, device_id=device_id, device_name=None,
                    statut=StatutDevice.ACTIVE, last_seen=datetime.utcnow()
                )
                db.session.add(device)
                user.device_id = device_id
                db.session.add(user)
                db.session.commit()
            else:
                return False, "Appareil non autorise"
        else:
            device.last_seen = datetime.utcnow()
            db.session.add(device)
            db.session.commit()
    return True, None


def _check_subscription_for_admin(tenant):
    if not tenant:
        return False, "Aucun tenant associe"
    now = datetime.utcnow()
    abonnement_actif = Abonnement.query.filter(
        Abonnement.tenant_id == tenant.id,
        Abonnement.statut == StatutAbonnement.ACTIF,
        Abonnement.date_fin > now,
        Abonnement.is_active == True
    ).first()
    if not abonnement_actif:
        if tenant.statut.value == "en_essai":
            return True, None
        return False, "Abonnement requis"
    return True, None


# ============================================================
# CREATION DE TOKEN AVEC VERSION MDP
# ============================================================

def _build_token_claims(user, tenant=None):
    """Construit les additional_claims pour create_access_token."""
    return {
        "username": user.username,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else user.role,
        "tenant_id": tenant.id if tenant else user.tenant_id,
        "tenant_slug": tenant.slug if tenant else None,
        # password version pour invalidation apres changement
        "pwd_v": user.token_version or 0,
    }


def create_access_token_for_user(user, tenant=None):
    return create_access_token(
        identity=user.id,
        additional_claims=_build_token_claims(user, tenant),
    )


# ============================================================
# AUTHENTIFICATION PRINCIPALE
# ============================================================

def authenticate_user(identifier, password, tenant_slug=None, device_id=None):
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

    allowed, error_msg = _check_admin_device(user, device_id=device_id, tenant=tenant)
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

    access_token = create_access_token(
        identity=user.id,
        additional_claims=_build_token_claims(user, tenant),
    )
    refresh_token = create_refresh_token(identity=user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict(),
        "tenant": tenant.to_dict() if tenant else None,
        "must_change_password": bool(user.must_change_password),
    }, None
