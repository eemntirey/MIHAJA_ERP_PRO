from functools import wraps
from flask_jwt_extended import get_jwt_identity, get_jwt, jwt_required
from app.models.utilisateur import Utilisateur, Role
from app.models.tenant import Tenant, StatutTenant
from app import db
from app.security.roles import has_permission as _has_permission_single
from app.security.plan_limits import resolve_tenant_context

# Correspondance entre namespace de permission et module d'abonnement.
# Les domaines sans entrée (profil, notifications, admin, reporting, etc.)
# restent accessibles indépendamment du plan.
_PERMISSION_TO_PLAN_MODULE = {
    'dashboard': 'dashboard',
    'product': 'produits',
    'client': 'clients',
    'sale': 'ventes',
    'invoice': 'factures',
    'payment': 'paiements',
    'stock': 'stocks',
    'quote': 'documents',
    'purchase_order': 'achats',
    'delivery': 'livraison',
    'compte': 'comptabilite',
    'ecriture': 'comptabilite',
    'tresorerie': 'comptabilite',
    'employe': 'rh',
    'presence': 'rh',
    'conge': 'rh',
    'salaire': 'rh',
    'prime': 'rh',
    'stagiaire': 'rh',
}

def _enforce_plan_module(user_id, permissions):
    """Bloque les accès directs à un module non inclus dans le plan."""
    user = db.session.get(Utilisateur, user_id)
    if not user or user.role == Role.SUPER_ADMIN:
        return None

    claims = get_jwt() or {}
    tenant_id = claims.get('tenant_id')
    if isinstance(tenant_id, str) and tenant_id.isdigit():
        tenant_id = int(tenant_id)
    if not tenant_id:
        return None

    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return None

    # Pendant l'essai, le projet autorise explicitement les modules pour
    # permettre la découverte du produit.
    if tenant.statut == StatutTenant.EN_ESSAI:
        return None

    _, _, modules = resolve_tenant_context(tenant)
    requested_modules = {
        _PERMISSION_TO_PLAN_MODULE.get(str(permission).split('.', 1)[0])
        for permission in permissions
    }
    requested_modules.discard(None)
    unavailable = sorted(module for module in requested_modules if module not in modules)
    if unavailable:
        return {
            'message': f'Module "{unavailable[0]}" non disponible pour votre abonnement actuel.',
            'module': unavailable[0],
        }, 403
    return None



def _user_has_permission(user_id, permission):
    """Reexport pour usage interne (un seul code path)."""
    return _has_permission_single(user_id, permission)


def permission_required(*permissions):
    """Décorateur pour vérifier les permissions effectives.

    Usage :
        @permission_required('sale.view')
        @permission_required('sale.view', 'sale.create')  # ANY-of
        @permission_required(['sale.view', 'sale.create'])  # ANY-of (liste)

    IMPORTANT : retourne un tuple (body, status) compatible Flask-RESTX
    (et non un objet Response), pour eviter une double serialisation
    par flask_restx.representations.output_json.
    """
    if len(permissions) == 1 and isinstance(permissions[0], (list, tuple)):
        perms_list = list(permissions[0])
    else:
        perms_list = list(permissions)

    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            user_id = get_jwt_identity()
            # ANY-of : si l'utilisateur a au moins une des permissions -> ok.
            granted = False
            for perm in perms_list:
                if _user_has_permission(user_id, perm):
                    granted = True
                    break
            if not granted:
                return {
                    'message': 'Permission non accordee',
                    'required_any_of': perms_list,
                }, 403
            module_error = _enforce_plan_module(user_id, perms_list)
            if module_error:
                return module_error
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permission_required_all(*permissions):
    """Variante ALL-of : l'utilisateur doit posseder toutes les permissions."""
    if len(permissions) == 1 and isinstance(permissions[0], (list, tuple)):
        perms_list = list(permissions[0])
    else:
        perms_list = list(permissions)

    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            user_id = get_jwt_identity()
            missing = [p for p in perms_list if not _user_has_permission(user_id, p)]
            if missing:
                return {
                    'message': 'Permission non accordee',
                    'missing': missing,
                }, 403
            module_error = _enforce_plan_module(user_id, perms_list)
            if module_error:
                return module_error
            return f(*args, **kwargs)
        return decorated_function
    return decorator