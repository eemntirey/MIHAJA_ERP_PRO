"""Tests du service de configuration PAPI par tenant (tenant_papi_service.py).

Couvre :
- get_papi_client_for_tenant (clé présente, absente, corrompue)
- get_webhook_secret_for_tenant (secret présent, absent)
- update_tenant_papi_settings (mise à jour, purge, environnement invalide)
- set_vitrine_enabled (conditions, refus, succès)
- test_tenant_papi_credentials (clé valide, invalide)
"""

import os
import uuid
from unittest.mock import patch, MagicMock

import pytest

from app import db
from app.models.tenant import Tenant, StatutTenant


@pytest.fixture(autouse=True)
def _set_encryption_key():
    """Définit ENCRYPTION_KEY pour les tests de chiffrement."""
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        os.environ['ENCRYPTION_KEY'] = key
    yield


@pytest.fixture
def tenant_with_papi(app):
    """Tenant actif avec clé PAPI configurée."""
    with app.app_context():
        from app.security.encryption import encrypt_text
        suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            nom=f'PapiTenant {suffix}',
            slug=f'papitenant-{suffix}',
            statut=StatutTenant.ACTIF,
            plan='pro',
            papi_api_key_encrypted=encrypt_text('pk_test_12345'),
            papi_webhook_secret_encrypted=encrypt_text('whsec_test_67890'),
            papi_environment='sandbox',
        )
        db.session.add(tenant)
        db.session.commit()
        return {'id': tenant.id, 'slug': tenant.slug}


@pytest.fixture
def tenant_no_papi(app):
    """Tenant actif sans clé PAPI."""
    with app.app_context():
        suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            nom=f'NoPapiTenant {suffix}',
            slug=f'nopapi-{suffix}',
            statut=StatutTenant.ACTIF,
            plan='pro',
        )
        db.session.add(tenant)
        db.session.commit()
        return {'id': tenant.id, 'slug': tenant.slug}


class TestGetPapiClientForTenant:

    def test_returns_client_with_key(self, app, tenant_with_papi):
        from app.services.tenant_papi_service import get_papi_client_for_tenant
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_with_papi['id'])
            client = get_papi_client_for_tenant(tenant)
            assert client is not None
            assert client.api_key == 'pk_test_12345'

    def test_returns_none_without_key(self, app, tenant_no_papi):
        from app.services.tenant_papi_service import get_papi_client_for_tenant
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_no_papi['id'])
            client = get_papi_client_for_tenant(tenant)
            assert client is None

    def test_raises_on_corrupted_key(self, app, tenant_no_papi):
        from app.services.tenant_papi_service import get_papi_client_for_tenant, TenantPapiConfigError
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_no_papi['id'])
            tenant.papi_api_key_encrypted = 'not-a-valid-fernet-token'
            db.session.commit()

            with pytest.raises(TenantPapiConfigError):
                get_papi_client_for_tenant(tenant)


class TestGetWebhookSecretForTenant:

    def test_returns_secret(self, app, tenant_with_papi):
        from app.services.tenant_papi_service import get_webhook_secret_for_tenant
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_with_papi['id'])
            secret = get_webhook_secret_for_tenant(tenant)
            assert secret == 'whsec_test_67890'

    def test_returns_none_without_secret(self, app, tenant_no_papi):
        from app.services.tenant_papi_service import get_webhook_secret_for_tenant
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_no_papi['id'])
            secret = get_webhook_secret_for_tenant(tenant)
            assert secret is None


class TestUpdateTenantPapiSettings:

    def test_update_settings(self, app, tenant_no_papi):
        from app.services.tenant_papi_service import update_tenant_papi_settings
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_no_papi['id'])
            update_tenant_papi_settings(
                tenant,
                papi_api_key='pk_new_key',
                papi_webhook_secret='whsec_new_secret',
                papi_environment='sandbox',
            )
            db.session.refresh(tenant)
            assert tenant.papi_api_key_encrypted is not None
            assert tenant.papi_webhook_secret_encrypted is not None
            assert tenant.papi_environment == 'sandbox'
            assert tenant.papi_configured_at is not None

    def test_clear_settings(self, app, tenant_with_papi):
        from app.services.tenant_papi_service import update_tenant_papi_settings
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_with_papi['id'])
            tenant.vitrine_enabled = True
            db.session.commit()

            update_tenant_papi_settings(tenant, clear=True)
            db.session.refresh(tenant)
            assert tenant.papi_api_key_encrypted is None
            assert tenant.papi_webhook_secret_encrypted is None
            assert tenant.vitrine_enabled is False

    def test_invalid_environment(self, app, tenant_no_papi):
        from app.services.tenant_papi_service import update_tenant_papi_settings
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_no_papi['id'])
            with pytest.raises(ValueError):
                update_tenant_papi_settings(
                    tenant,
                    papi_api_key='pk_key',
                    papi_environment='uat',
                )


class TestSetVitrineEnabled:

    def test_enable_requires_papi(self, app, tenant_no_papi):
        from app.services.tenant_papi_service import set_vitrine_enabled, TenantPapiConfigError
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_no_papi['id'])
            with pytest.raises(TenantPapiConfigError):
                set_vitrine_enabled(tenant, True)

    def test_enable_rejects_inactive_tenant(self, app, tenant_with_papi):
        from app.services.tenant_papi_service import set_vitrine_enabled, TenantPapiConfigError
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_with_papi['id'])
            tenant.statut = StatutTenant.INACTIF
            db.session.commit()

            with pytest.raises(TenantPapiConfigError):
                set_vitrine_enabled(tenant, True)

    def test_enable_success(self, app, tenant_with_papi):
        from app.services.tenant_papi_service import set_vitrine_enabled
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_with_papi['id'])
            set_vitrine_enabled(tenant, True)
            db.session.refresh(tenant)
            assert tenant.vitrine_enabled is True
            assert tenant.vitrine_enabled_at is not None

    def test_disable(self, app, tenant_with_papi):
        from app.services.tenant_papi_service import set_vitrine_enabled
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_with_papi['id'])
            set_vitrine_enabled(tenant, True)
            set_vitrine_enabled(tenant, False)
            db.session.refresh(tenant)
            assert tenant.vitrine_enabled is False


class TestTestTenantPapiCredentials:

    def test_valid_key(self, app, tenant_with_papi):
        from app.services.tenant_papi_service import test_tenant_papi_credentials
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_with_papi['id'])
            mock_client = MagicMock()
            mock_client.create_payment_link.return_value = {'paymentLink': 'ok'}
            with patch(
                'app.services.tenant_papi_service.get_papi_client_for_tenant',
                return_value=mock_client,
            ):
                result = test_tenant_papi_credentials(tenant)
            assert result is True

    def test_invalid_key(self, app, tenant_with_papi):
        from app.services.tenant_papi_service import test_tenant_papi_credentials
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_with_papi['id'])
            mock_client = MagicMock()
            from app.services.papi.errors import PapiAuthError
            mock_client.create_payment_link.side_effect = PapiAuthError('Unauthorized')
            with patch(
                'app.services.tenant_papi_service.get_papi_client_for_tenant',
                return_value=mock_client,
            ):
                result = test_tenant_papi_credentials(tenant)
            assert result is False
