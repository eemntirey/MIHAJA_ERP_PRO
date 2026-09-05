from functools import wraps
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.models.utilisateur import Utilisateur, Role
from app.security.roles import has_permission as _has_permission_single


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
            return f(*args, **kwargs)
        return decorated_function
    return decorator