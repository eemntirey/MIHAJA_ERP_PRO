from functools import wraps
from flask import g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from flask_jwt_extended.exceptions import (
    NoAuthorizationError,
    InvalidHeaderError,
    RevokedTokenError,
    JWTDecodeError,
)
from app.models.tenant import Tenant
from app.models.utilisateur import Role, Utilisateur

FEATURE_LIMIT_MAP = {
    'produits': ('max_produits', 'produit'),
    'clients': ('max_clients', 'client'),
    'utilisateurs': ('max_utilisateurs', 'utilisateur'),
}


def check_plan_limits(feature):
    """
    Décorateur vérifiant les limites du plan du tenant
    avant une action de création.

    Le rôle SUPER_ADMIN contourne automatiquement la vérification.

    Args:
        feature: 'produits', 'clients' ou 'utilisateurs'

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

            utilisateur = Utilisateur.query.get(user_id)

            if utilisateur and utilisateur.role == Role.SUPER_ADMIN:
                return fn(*args, **kwargs)

            tenant = getattr(g, 'current_tenant', None)
            if not tenant:
                tenant_id = claims.get('tenant_id')
                if isinstance(tenant_id, str) and tenant_id.isdigit():
                    tenant_id = int(tenant_id)
                if not tenant_id and utilisateur:
                    tenant_id = utilisateur.tenant_id
                if not tenant_id:
                    return {'message': 'Aucun tenant associe a ce compte'}, 401
                tenant = Tenant.query.get(tenant_id)
                if not tenant:
                    return {'message': 'Tenant introuvable'}, 401

            limit = getattr(tenant, limit_field)
            if limit is None or limit <= 0:
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
                    'message': 'Limite de clients atteinte pour votre abonnement actuel.'
                }, 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator
