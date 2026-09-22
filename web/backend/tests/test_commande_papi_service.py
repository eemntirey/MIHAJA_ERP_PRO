"""Tests du service de paiement PAPI pour commandes vitrine (commande_papi_service.py).

Couvre :
- parse_papi_reference (CMD, SUB, invalide)
- create_commande_papi_payment (succès, tenant sans PAPI, vitrine désactivée, méthode invalide, idempotence, erreur PAPI)
"""

import os
import re
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

from app import db
from app.models.tenant import Tenant, StatutTenant
from app.models.commande_client import CommandeClient, StatutCommande
from app.models.paiement import Paiement, StatutPaiement


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
def tenant_papi_vitrine(app):
    """Tenant actif avec PAPI configuré et vitrine activée."""
    with app.app_context():
        from app.security.encryption import encrypt_text
        suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            nom=f'VitrineTenant {suffix}',
            slug=f'vitrine-{suffix}',
            statut=StatutTenant.ACTIF,
            plan='pro',
            papi_api_key_encrypted=encrypt_text('pk_test_vitrine'),
            papi_webhook_secret_encrypted=encrypt_text('whsec_vitrine'),
            papi_environment='sandbox',
            vitrine_enabled=True,
        )
        db.session.add(tenant)
        db.session.commit()
        return {'id': tenant.id, 'slug': tenant.slug}


@pytest.fixture
def commande_for_papi(app, tenant_papi_vitrine):
    """CommandeClient pour les tests de paiement PAPI."""
    with app.app_context():
        suffix = uuid.uuid4().hex[:8]
        commande = CommandeClient(
            reference=f'CMD-{suffix}',
            nom_client='Rakoto',
            prenom_client='Marie',
            email_client=f'rakoto-{suffix}@example.com',
            telephone_client='+261340000000',
            items='[{"produit_id": 1, "quantite": 2, "prix_unitaire": 40000.0}]',
            total_ht=80000.0,
            total_ttc=96000.0,
            statut=StatutCommande.EN_ATTENTE,
            tenant_id=tenant_papi_vitrine['id'],
        )
        db.session.add(commande)
        db.session.commit()
        return {
            'id': commande.id,
            'reference': commande.reference,
            'tenant_id': tenant_papi_vitrine['id'],
        }


class TestParsePapiReference:

    def test_parse_cmd_reference(self):
        from app.services.commande_papi_service import parse_papi_reference
        result = parse_papi_reference('CMD-3-5-A1B2C3D4')
        assert result is not None
        assert result['kind'] == 'cmd'
        assert result['tenant_id'] == 3
        assert result['entity_id'] == 5

    def test_parse_sub_reference(self):
        from app.services.commande_papi_service import parse_papi_reference
        result = parse_papi_reference('SUB-3-7-X9Y8Z7W6')
        assert result is not None
        assert result['kind'] == 'sub'
        assert result['tenant_id'] == 3
        assert result['entity_id'] == 7

    def test_parse_invalid_reference(self):
        from app.services.commande_papi_service import parse_papi_reference
        result = parse_papi_reference('INVALID-REF')
        assert result is None

    def test_parse_empty_reference(self):
        from app.services.commande_papi_service import parse_papi_reference
        result = parse_papi_reference('')
        assert result is None


class TestCreateCommandePapiPayment:

    def test_create_payment_success(self, app, tenant_papi_vitrine, commande_for_papi):
        from app.services.commande_papi_service import create_commande_papi_payment

        fake_client = MagicMock()
        fake_client.create_payment_link.return_value = {
            'paymentLink': 'https://pay.papi.mg/fake',
            'paymentReference': f'CMD-{tenant_papi_vitrine["id"]}-{commande_for_papi["id"]}-ABC123',
            'notificationToken': 'nt-fake-token',
            'amount': 96000.0,
        }

        with app.app_context():
            with patch(
                'app.services.commande_papi_service.get_papi_client_for_tenant',
                return_value=fake_client,
            ):
                result = create_commande_papi_payment(
                    commande_id=commande_for_papi['id'],
                    payment_method='MVOLA',
                    customer_name='Rakoto Marie',
                    customer_email='rakoto@test.mg',
                    customer_phone='+261340000000',
                )

            assert result is not None
            assert result['payment_link'] == 'https://pay.papi.mg/fake'
            assert result['payment']['provider'] == 'papi'
            assert result['payment']['statut'] == StatutPaiement.EN_ATTENTE.value

    def test_create_payment_tenant_no_papi(self, app):
        from app.services.commande_papi_service import create_commande_papi_payment, CommandePapiError
        with app.app_context():
            suffix = uuid.uuid4().hex[:8]
            tenant = Tenant(
                nom=f'NoPapi {suffix}',
                slug=f'nopapi-{suffix}',
                statut=StatutTenant.ACTIF,
                plan='pro',
            )
            db.session.add(tenant)
            db.session.flush()

            commande = CommandeClient(
                reference=f'CMD-{suffix}',
                nom_client='Test',
                email_client='test@test.mg',
                items='[]',
                total_ht=0,
                total_ttc=0,
                tenant_id=tenant.id,
            )
            db.session.add(commande)
            db.session.commit()

            with pytest.raises(CommandePapiError, match='PAPI'):
                create_commande_papi_payment(
                    commande_id=commande.id,
                    payment_method='MVOLA',
                    customer_name='Test',
                    customer_email='test@test.mg',
                    customer_phone='+261340000000',
                )

    def test_create_payment_vitrine_disabled(self, app):
        from app.services.commande_papi_service import create_commande_papi_payment, CommandePapiError
        with app.app_context():
            from app.security.encryption import encrypt_text
            suffix = uuid.uuid4().hex[:8]
            tenant = Tenant(
                nom=f'VitOff {suffix}',
                slug=f'vitoff-{suffix}',
                statut=StatutTenant.ACTIF,
                plan='pro',
                papi_api_key_encrypted=encrypt_text('pk_test'),
                vitrine_enabled=False,
            )
            db.session.add(tenant)
            db.session.flush()

            commande = CommandeClient(
                reference=f'CMD-{suffix}',
                nom_client='Test',
                email_client='test@test.mg',
                items='[]',
                total_ht=0,
                total_ttc=0,
                tenant_id=tenant.id,
            )
            db.session.add(commande)
            db.session.commit()

            with pytest.raises(CommandePapiError, match='vitrine'):
                create_commande_papi_payment(
                    commande_id=commande.id,
                    payment_method='MVOLA',
                    customer_name='Test',
                    customer_email='test@test.mg',
                    customer_phone='+261340000000',
                )

    def test_create_payment_invalid_method(self, app, tenant_papi_vitrine, commande_for_papi):
        from app.services.commande_papi_service import create_commande_papi_payment
        with app.app_context():
            with pytest.raises(ValueError):
                create_commande_papi_payment(
                    commande_id=commande_for_papi['id'],
                    payment_method='BITCOIN',
                    customer_name='Test',
                    customer_email='test@test.mg',
                    customer_phone='+261340000000',
                )

    def test_create_payment_idempotent(self, app, tenant_papi_vitrine, commande_for_papi):
        from app.services.commande_papi_service import create_commande_papi_payment

        fake_client = MagicMock()
        fake_client.create_payment_link.return_value = {
            'paymentLink': 'https://pay.papi.mg/fake',
            'paymentReference': f'CMD-{tenant_papi_vitrine["id"]}-{commande_for_papi["id"]}-IDEM1',
            'notificationToken': 'nt-idem',
            'amount': 96000.0,
        }

        with app.app_context():
            with patch(
                'app.services.commande_papi_service.get_papi_client_for_tenant',
                return_value=fake_client,
            ):
                result1 = create_commande_papi_payment(
                    commande_id=commande_for_papi['id'],
                    payment_method='MVOLA',
                    customer_name='Test',
                    customer_email='test@test.mg',
                    customer_phone='+261340000000',
                )
                result2 = create_commande_papi_payment(
                    commande_id=commande_for_papi['id'],
                    payment_method='MVOLA',
                    customer_name='Test',
                    customer_email='test@test.mg',
                    customer_phone='+261340000000',
                )

            assert result1['payment']['id'] == result2['payment']['id']

    def test_create_payment_reference_format(self, app, tenant_papi_vitrine, commande_for_papi):
        from app.services.commande_papi_service import create_commande_papi_payment

        fake_client = MagicMock()
        fake_client.create_payment_link.return_value = {
            'paymentLink': 'https://pay.papi.mg/fake',
            'paymentReference': f'CMD-{tenant_papi_vitrine["id"]}-{commande_for_papi["id"]}-FMT123',
            'notificationToken': 'nt-fmt',
            'amount': 96000.0,
        }

        with app.app_context():
            with patch(
                'app.services.commande_papi_service.get_papi_client_for_tenant',
                return_value=fake_client,
            ):
                result = create_commande_papi_payment(
                    commande_id=commande_for_papi['id'],
                    payment_method='ORANGE_MONEY',
                    customer_name='Test',
                    customer_email='test@test.mg',
                    customer_phone='+261340000000',
                )

            ref = fake_client.calls[0]['reference']
            assert ref.startswith(f'CMD-{tenant_papi_vitrine["id"]}-')

    def test_create_payment_papi_error(self, app, tenant_papi_vitrine, commande_for_papi):
        from app.services.commande_papi_service import create_commande_papi_payment, CommandePapiError
        from app.services.papi.errors import PapiUnavailableError

        fake_client = MagicMock()
        fake_client.create_payment_link.side_effect = PapiUnavailableError('Timeout')

        with app.app_context():
            with patch(
                'app.services.commande_papi_service.get_papi_client_for_tenant',
                return_value=fake_client,
            ):
                with pytest.raises(CommandePapiError):
                    create_commande_papi_payment(
                        commande_id=commande_for_papi['id'],
                        payment_method='MVOLA',
                        customer_name='Test',
                        customer_email='test@test.mg',
                        customer_phone='+261340000000',
                    )
