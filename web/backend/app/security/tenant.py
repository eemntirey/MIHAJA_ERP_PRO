from functools import wraps
from flask import request, g
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur, StatutAdmin
from app.models.admin_device import AdminDevice, StatutDevice
from app import db
from sqlalchemy import event
import logging
from app.security.roles import is_super_admin, is_admin, is_manager

logger = logging.getLogger(__name__)

# Global flag to track if the tenant filter event is registered
_tenant_filter_registered = False


def register_tenant_filter_event():
    """Register the global SQLAlchemy event listener for tenant filtering.
    This should be called once during app initialization.
    """
    global _tenant_filter_registered
    if _tenant_filter_registered:
        return
    
    @event.listens_for(db.session, 'do_orm_execute')
    def _do_orm_execute(orm_execute_state):
        # Skip if not a select statement
        if not orm_execute_state.is_select:
            return
        
        # Skip if execution options indicate no tenant filtering
        if orm_execute_state.execution_options.get('_skip_tenant_filter'):
            logger.warning(
                "Tenant filter bypassed via _skip_tenant_filter on query: %s",
                str(orm_execute_state.statement),
            )
            return
        
        # Get current tenant from Flask g
        from flask import has_request_context
        if not has_request_context():
            return
        
        tenant = getattr(g, 'current_tenant', None)
        if tenant is None:
            # No tenant filtering for SUPER_ADMIN (g.current_tenant is None)
            return
        
        tenant_id = getattr(g, 'current_tenant_id', None)
        if tenant_id is None:
            try:
                tenant_id = tenant.id
            except Exception:
                return
        
        # Apply tenant filter to all entities in the query that have tenant_id
        if hasattr(orm_execute_state.statement, 'column_descriptions'):
            for desc in orm_execute_state.statement.column_descriptions:
                entity = desc.get('entity')
                if entity is None:
                    continue
                if entity.__name__ == 'Tenant':
                    continue
                if hasattr(entity, 'tenant_id'):
                    orm_execute_state.statement = orm_execute_state.statement.where(
                        entity.tenant_id == tenant_id
                    )
    
    _tenant_filter_registered = True


def get_current_tenant():
    return getattr(g, 'current_tenant', None)


def get_current_tenant_id():
    return getattr(g, 'current_tenant_id', None)


def set_tenant_filter(query, model_class):
    tenant_id = get_current_tenant_id()
    if tenant_id is not None:
        if hasattr(model_class, 'tenant_id'):
            query = query.filter(model_class.tenant_id == tenant_id)
    return query


def tenant_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
        from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError, RevokedTokenError, JWTDecodeError

        try:
            verify_jwt_in_request()
        except NoAuthorizationError:
            return {'message': 'En-tête Authorization manquant ou invalide'}, 401
        except InvalidHeaderError:
            return {'message': 'En-tête Authorization invalide'}, 401
        except RevokedTokenError:
            return {'message': 'Token JWT révoqué'}, 401
        except JWTDecodeError:
            return {'message': 'Token JWT invalide'}, 401
        except Exception:
            return {'message': 'Token JWT invalide ou expiré'}, 401

        claims = get_jwt()
        tenant_id = claims.get('tenant_id')
        user_id = get_jwt_identity()

        if isinstance(tenant_id, str) and tenant_id.isdigit():
            tenant_id = int(tenant_id)
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)

        utilisateur = db.session.get(Utilisateur, user_id)
        
        if utilisateur and is_super_admin(utilisateur.role):
            g.current_tenant = None
            g.current_user = utilisateur
            return fn(*args, **kwargs)

        if not tenant_id:
            if getattr(g, 'current_tenant', None):
                tenant_id = g.current_tenant.id
            else:
                if utilisateur and utilisateur.tenant_id:
                    tenant_id = utilisateur.tenant_id

        if not tenant_id:
            return {'message': 'Aucun tenant associe a ce compte'}, 401

        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Tenant introuvable'}, 401
        if not tenant.is_active or tenant.statut in (StatutTenant.INACTIF, StatutTenant.BLOQUE):
            return {'message': 'Tenant inactif'}, 401

        if not utilisateur:
            return {'message': 'Utilisateur introuvable'}, 401
        if utilisateur.tenant_id != tenant_id:
            return {'message': 'Acces refuse a ce tenant'}, 403
        
        if utilisateur.role not in [Role.SUPER_ADMIN, Role.USER, Role.ACCOUNTANT]:
            from app.models.abonnement import Abonnement, StatutAbonnement
            from datetime import datetime
            now = datetime.utcnow()
            abonnement_actif = Abonnement.query.filter(
                Abonnement.tenant_id == tenant_id,
                Abonnement.statut == StatutAbonnement.ACTIF,
                Abonnement.date_fin > now,
                Abonnement.is_active == True
            ).first()
            if not abonnement_actif:
                if tenant.statut != StatutTenant.EN_ESSAI:
                    return {'message': 'Abonnement requis'}, 403
        
        if utilisateur.role == Role.ADMIN:
            if utilisateur.admin_statut is not None and utilisateur.admin_statut != StatutAdmin.ACTIVE:
                return {'message': 'Administrateur suspendu ou revoque'}, 403

            has_any_device = AdminDevice.query.filter_by(user_id=utilisateur.id).first() is not None
            if not has_any_device:
                pass
            else:
                if not utilisateur.device_id:
                    return {'message': 'Appareil non enregistre'}, 403
                device = AdminDevice.query.filter_by(
                    user_id=utilisateur.id,
                    device_id=utilisateur.device_id,
                    statut=StatutDevice.ACTIVE
                ).first()
                if not device:
                    return {'message': 'Appareil non autorise'}, 403
                # Mise a jour last_seen sans commit immediat : le commit
                # sera declenche par la transaction en cours, ce qui
                # elimine une requete par appel authentifie.
                device.last_seen = datetime.utcnow()
        
        g.current_tenant = tenant
        g.current_tenant_id = tenant_id
        g.current_user = utilisateur

        return fn(*args, **kwargs)

    return wrapper


READONLY_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}


def super_admin_readonly(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from flask_jwt_extended import get_jwt
        from app.security.roles import is_super_admin

        claims = get_jwt() or {}
        role = claims.get('role')

        if is_super_admin(role):
            if request.method in READONLY_METHODS:
                return {'message': 'Acces en lecture seule pour le super administrateur'}, 403
        return fn(*args, **kwargs)
    return wrapper


def tenant_required_readonly(fn):
    return tenant_required(super_admin_readonly(fn))


def tenant_admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
        from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError, RevokedTokenError, JWTDecodeError

        try:
            verify_jwt_in_request()
        except NoAuthorizationError:
            return {'message': 'En-tête Authorization manquant ou invalide'}, 401
        except InvalidHeaderError:
            return {'message': 'En-tête Authorization invalide'}, 401
        except RevokedTokenError:
            return {'message': 'Token JWT révoqué'}, 401
        except JWTDecodeError:
            return {'message': 'Token JWT invalide'}, 401
        except Exception:
            return {'message': 'Token JWT invalide ou expiré'}, 401

        user_id = get_jwt_identity()
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)

        utilisateur = db.session.get(Utilisateur, user_id)
        if not utilisateur or not utilisateur.is_admin:
            return {'message': 'Acces refuse: admin requis'}, 403

        g.current_user = utilisateur
        return fn(*args, **kwargs)

    return wrapper


def get_current_tenant_id_or_none():
    """Retourne le tenant_id courant ou None pour SUPER_ADMIN (pas de filtrage)."""
    tenant = get_current_tenant()
    return tenant.id if tenant else None


def tenant_filtered_get(model_class, obj_id, allow_super_admin=True):
    """Récupère un objet en appliquant le filtre tenant.

    Pour SUPER_ADMIN, le filtre tenant n'est pas appliqué (accès global).
    """
    from flask_jwt_extended import get_jwt
    from app.security.roles import is_super_admin

    claims = get_jwt() or {}
    role = claims.get('role')

    query = model_class.query.filter_by(id=obj_id, is_active=True)
    if not (allow_super_admin and is_super_admin(role)):
        tenant_id = get_current_tenant_id_or_none()
        if tenant_id is not None and hasattr(model_class, 'tenant_id'):
            query = query.filter_by(tenant_id=tenant_id)
    return query.first()


def resolve_tenant_from_header():
    tenant_slug = request.headers.get('X-Tenant-Slug')
    tenant_domaine = request.headers.get('X-Tenant-Domaine')
    
    if tenant_slug:
        return Tenant.query.filter_by(slug=tenant_slug, is_active=True).first()
    elif tenant_domaine:
        return Tenant.query.filter_by(domaine=tenant_domaine, is_active=True).first()
    return None


def ensure_tenant_for_model(model_instance):
    tenant_id = get_current_tenant_id()
    if tenant_id and hasattr(model_instance, 'tenant_id'):
        model_instance.tenant_id = tenant_id


def subscription_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
        from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError, RevokedTokenError, JWTDecodeError

        try:
            verify_jwt_in_request()
        except NoAuthorizationError:
            return {'message': 'En-tête Authorization manquant ou invalide'}, 401
        except InvalidHeaderError:
            return {'message': 'En-tête Authorization invalide'}, 401
        except RevokedTokenError:
            return {'message': 'Token JWT révoqué'}, 401
        except JWTDecodeError:
            return {'message': 'Token JWT invalide'}, 401
        except Exception:
            return {'message': 'Token JWT invalide ou expiré'}, 401

        user_id = get_jwt_identity()
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)

        utilisateur = db.session.get(Utilisateur, user_id)
        if not utilisateur:
            return {'message': 'Utilisateur introuvable'}, 401

        if is_admin(utilisateur.role) or is_manager(utilisateur.role):
            return fn(*args, **kwargs)

        tenant_id = utilisateur.tenant_id
        if not tenant_id:
            return {'message': 'Aucun tenant associe a ce compte'}, 401

        from app.models.abonnement import Abonnement, StatutAbonnement
        from datetime import datetime
        now = datetime.utcnow()

        abonnement_actif = Abonnement.query.filter(
            Abonnement.tenant_id == tenant_id,
            Abonnement.statut == StatutAbonnement.ACTIF,
            Abonnement.date_fin > now,
            Abonnement.is_active == True
        ).first()

        if not abonnement_actif:
            tenant = db.session.get(Tenant, tenant_id)
            if tenant and tenant.statut == StatutTenant.EN_ESSAI:
                return fn(*args, **kwargs)
            return {'message': 'Abonnement requis'}, 403

        return fn(*args, **kwargs)
    
    return wrapper
