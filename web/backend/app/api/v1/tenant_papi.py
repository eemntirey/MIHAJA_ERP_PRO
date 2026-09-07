"""Endpoints de configuration Papi pour le tenant courant.

Permet à l'administrateur principal d'un tenant de :
- Consulter le statut de sa configuration Papi (sans exposer la clé).
- Mettre à jour / supprimer ses clés Papi (clé API, secret webhook,
  environnement).
- Tester la connectivité avec Papi.
- Activer / désactiver la vitrine publique.

Sécurité : ``tenant_required`` + filtre ``is_principal_admin`` pour
s'assurer qu'un simple manager ne peut pas modifier ces paramètres
critiques.
"""

from flask import request, current_app
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app import db
from app.models.utilisateur import Utilisateur, Role
from app.models.tenant import Tenant
from app.security.tenant import (
    get_current_tenant,
    get_current_tenant_id,
    tenant_required,
)
from app.services.tenant_papi_service import (
    TenantPapiConfigError,
    set_vitrine_enabled,
    test_tenant_papi_credentials,
    update_tenant_papi_settings,
)


ns = Namespace(
    'tenant_papi',
    description='Configuration Papi marchand du tenant (admin principal)',
)


def _is_principal_admin(user: Utilisateur, tenant: Tenant) -> bool:
    """Vérifie que l'utilisateur est bien l'admin principal du tenant."""
    if not user or not tenant:
        return False
    role = user.role.value if hasattr(user.role, 'value') else user.role
    if role != Role.ADMIN.value:
        return False
    return bool(
        getattr(user, 'is_principal_admin', False)
        or tenant.admin_principal_id == user.id
    )


def _require_principal_admin():
    """Décorateur logique : retourne (user, tenant, error)."""
    claims = get_jwt() or {}
    user_id = claims.get('sub') or get_jwt_identity()
    user = db.session.get(Utilisateur, int(user_id)) if user_id else None
    tenant = get_current_tenant()
    if not user or not tenant:
        return None, None, ({'message': 'Non autorise'}, 403)
    if not _is_principal_admin(user, tenant):
        return user, tenant, (
            {'message': 'Seul l\'administrateur principal peut modifier ces paramètres'},
            403,
        )
    return user, tenant, None


@ns.route('/me/papi-settings')
class TenantPapiSettings(Resource):

    @jwt_required()
    @tenant_required
    def get(self):
        """Retourne le statut Papi / vitrine (clé jamais en clair)."""
        user, tenant, err = _require_principal_admin()
        if err:
            return err
        return tenant.to_papi_status_dict(), 200

    @jwt_required()
    @tenant_required
    def put(self):
        """Mise à jour des identifiants Papi marchand du tenant."""
        user, tenant, err = _require_principal_admin()
        if err:
            return err

        data = request.get_json() or {}
        try:
            tenant = update_tenant_papi_settings(
                tenant,
                papi_api_key=data.get('papi_api_key'),
                papi_webhook_secret=data.get('papi_webhook_secret'),
                papi_environment=data.get('papi_environment'),
                clear=bool(data.get('clear')),
            )
        except TenantPapiConfigError as exc:
            return {'message': str(exc)}, 400
        except ValueError as exc:
            return {'message': str(exc)}, 400

        return tenant.to_papi_status_dict(), 200


@ns.route('/me/papi-settings/test')
class TenantPapiSettingsTest(Resource):

    @jwt_required()
    @tenant_required
    def post(self):
        """Teste la clé Papi du tenant via un appel réel léger."""
        user, tenant, err = _require_principal_admin()
        if err:
            return err
        try:
            result = test_tenant_papi_credentials(tenant)
        except TenantPapiConfigError as exc:
            return {'message': str(exc), 'ok': False}, 400
        return {'ok': True, **result}, 200


@ns.route('/me/vitrine')
class TenantVitrineToggle(Resource):

    @jwt_required()
    @tenant_required
    def get(self):
        user, tenant, err = _require_principal_admin()
        if err:
            return err
        return tenant.to_papi_status_dict(), 200

    @jwt_required()
    @tenant_required
    def put(self):
        """Active / désactive la vitrine publique du tenant."""
        user, tenant, err = _require_principal_admin()
        if err:
            return err
        data = request.get_json() or {}
        enabled = bool(data.get('enabled'))
        try:
            tenant = set_vitrine_enabled(tenant, enabled)
        except TenantPapiConfigError as exc:
            return {'message': str(exc)}, 400
        return tenant.to_papi_status_dict(), 200
