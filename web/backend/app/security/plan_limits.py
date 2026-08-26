from functools import wraps
from flask import g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from flask_jwt_extended.exceptions import (
    NoAuthorizationError,
    InvalidHeaderError,
    RevokedTokenError,
    JWTDecodeError,
)
from app import db
from app.models.tenant import Tenant
from app.models.utilisateur import Role, Utilisateur
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.roles import is_super_admin
from app.security.plans import resolve_limits, resolve_modules, is_unlimited
from app.models.tenant import StatutTenant

FEATURE_LIMIT_MAP = {
    'produits': ('max_produits', 'produit'),
    'clients': ('max_clients', 'client'),
    'utilisateurs': ('max_utilisateurs', 'utilisateur'),
    'employes': ('max_employees', 'employe'),
    'stagiaires': ('max_interns', 'stagiaire'),
}

FEATURE_LIMIT_MESSAGES = {
    'produits': 'Limite de produits atteinte pour votre abonnement actuel.',
    'clients': 'Limite de clients atteinte pour votre abonnement actuel.',
    'utilisateurs': 'Limite d\'utilisateurs atteinte pour votre abonnement actuel.',
    'employes': 'Limite d\'employés atteinte pour votre abonnement actuel.',
    'stagiaires': 'Limite de stagiaires atteinte pour votre abonnement actuel.',
}


def _get_tenant_from_claims_or_g():
    claims = get_jwt() or {}
    tenant = getattr(g, 'current_tenant', None)
    if tenant:
        return tenant
    tenant_id = claims.get('tenant_id')
    if isinstance(tenant_id, str) and tenant_id.isdigit():
        tenant_id = int(tenant_id)
    if not tenant_id:
        return None
    return db.session.get(Tenant, tenant_id)


def _get_active_abonnement(tenant):
    if not tenant:
        return None
    return Abonnement.query.filter(
        Abonnement.tenant_id == tenant.id,
        Abonnement.statut == StatutAbonnement.ACTIF,
        Abonnement.is_active == True,
    ).order_by(Abonnement.created_at.desc()).first()


def _get_limits(tenant):
    abonnement = _get_active_abonnement(tenant)
    if abonnement:
        return resolve_limits(tenant, abonnement)
    return resolve_limits(tenant)


def _get_modules(tenant):
    abonnement = _get_active_abonnement(tenant)
    if abonnement:
        return resolve_modules(tenant, abonnement)
    return resolve_modules(tenant)


def check_plan_limits(feature):
    """
    Décorateur vérifiant les limites du plan du tenant
    avant une action de création.

    Le rôle SUPER_ADMIN contourne automatiquement la vérification.

    Args:
        feature: 'produits', 'clients', 'utilisateurs', 'employes' ou 'stagiaires'

    Returns:
        Tuple (dict, int) avec une erreur 403 si la limite est atteinte,
        sinon poursuit l'exécution de la vue.
    """
    if feature not in FEATURE_LIMIT_MAP:
        raise ValueError(
            f"Feature inconnue: {feature}. "
            f"Options: {list(FEATURE_LIMIT_MAP.keys())}"
        )

    limit_field, model_name = FEATURE_LIMIT_MAP[feature]

    _MODEL_IMPORTS = {
        'produit': ('app.models.produit', 'Produit'),
        'client': ('app.models.client', 'Client'),
        'utilisateur': ('app.models.utilisateur', 'Utilisateur'),
        'employe': ('app.models.employe', 'Employe'),
        'stagiaire': ('app.models.stagiaire', 'Stagiaire'),
    }

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except NoAuthorizationError:
                return {
                    'message': 'En-tête Authorization manquant ou invalide'
                }, 401
            except InvalidHeaderError:
                return {'message': 'En-tête Authorization invalide'}, 401
            except RevokedTokenError:
                return {'message': 'Token JWT révoqué'}, 401
            except JWTDecodeError:
                return {'message': 'Token JWT invalide'}, 401
            except Exception:
                return {'message': 'Token JWT invalide ou expiré'}, 401

            claims = get_jwt()
            user_id = get_jwt_identity()
            if isinstance(user_id, str) and user_id.isdigit():
                user_id = int(user_id)

            utilisateur = db.session.get(Utilisateur, user_id)

            if utilisateur and is_super_admin(utilisateur.role):
                return fn(*args, **kwargs)

            tenant = _get_tenant_from_claims_or_g()
            if not tenant:
                return {'message': 'Aucun tenant associe a ce compte'}, 401

            limits = _get_limits(tenant)
            limit = limits.get(limit_field)
            if is_unlimited(limit):
                return fn(*args, **kwargs)

            module_name, class_name = _MODEL_IMPORTS[model_name]
            mod = __import__(module_name, fromlist=[class_name])
            model_class = getattr(mod, class_name)

            current_count = model_class.query.filter_by(
                tenant_id=tenant.id,
                is_active=True,
            ).count()

            if current_count >= limit:
                return {
                    'message': FEATURE_LIMIT_MESSAGES.get(feature, 'Limite atteinte pour votre abonnement actuel.')
                }, 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def is_admin_limit_reached(tenant):
    limits = _get_limits(tenant)
    admin_limit_val = limits.get('max_admins', 1)
    if admin_limit_val is None or admin_limit_val <= 0:
        admin_limit_val = 1

    current_admins = Utilisateur.query.filter(
        Utilisateur.tenant_id == tenant.id,
        Utilisateur.role == Role.ADMIN,
        Utilisateur.is_active == True,
    ).count()

    return current_admins >= admin_limit_val


def check_admin_limit():
    """
    Décorateur vérifiant que le tenant n'a pas atteint la limite d'administrateurs.
    Utilisé lors de la création/modification d'un utilisateur avec role ADMIN.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                return {'message': 'Token JWT invalide ou expiré'}, 401

            claims = get_jwt()
            user_id = get_jwt_identity()
            if isinstance(user_id, str) and user_id.isdigit():
                user_id = int(user_id)

            utilisateur = db.session.get(Utilisateur, user_id)
            if utilisateur and is_super_admin(utilisateur.role):
                return fn(*args, **kwargs)

            tenant = _get_tenant_from_claims_or_g()
            if not tenant:
                return {'message': 'Aucun tenant associe a ce compte'}, 401

            if is_admin_limit_reached(tenant):
                return {
                    'message': 'Limite d\'administrateurs atteinte pour votre abonnement actuel.'
                }, 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def require_module(module):
    """
    Décorateur vérifiant que le module est autorisé pour le tenant.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                return {'message': 'Token JWT invalide ou expiré'}, 401

            claims = get_jwt()
            user_id = get_jwt_identity()
            if isinstance(user_id, str) and user_id.isdigit():
                user_id = int(user_id)

            utilisateur = db.session.get(Utilisateur, user_id)
            if utilisateur and is_super_admin(utilisateur.role):
                return fn(*args, **kwargs)

            tenant = _get_tenant_from_claims_or_g()
            if not tenant:
                return {'message': 'Aucun tenant associe a ce compte'}, 401

            if tenant.statut == StatutTenant.EN_ESSAI:
                return fn(*args, **kwargs)

            allowed = _get_modules(tenant)
            if module not in allowed:
                return {
                    'message': f'Module "{module}" non disponible pour votre abonnement actuel.'
                }, 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator
