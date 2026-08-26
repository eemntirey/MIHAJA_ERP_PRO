
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app import db
from app.models.paiement import Paiement, StatutPaiement, TypePaiement, ProviderPaiement
from app.models.payment_event import PaymentEvent
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.security.auth import hash_password


@pytest.fixture
def auth_headers(app):
    with app.app_context():
        unique_slug = f'test-tenant-{uuid.uuid4().hex[:8]}'
        unique_email = f'test-{uuid.uuid4().hex[:8]}@example.com'
        unique_username = f'testuser-{uuid.uuid4().hex[:8]}'
        tenant = Tenant(
            nom='Test Tenant',
            slug=unique_slug,
            statut=StatutTenant.ACTIF,
            plan='starter',
        )
        db.session.add(tenant)
        db.session.flush()

        user = Utilisateur(
            username=unique_username,
            email=unique_email,
            password_hash=hash_password('password123'),
            role=Role.ADMIN,
            tenant_id=tenant.id,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(user)
        db.session.flush()

        abonnement = Abonnement(
            tenant_id=tenant.id,
            montant=15000.0,
            devise='MGA',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.EN_ATTENTE,
            plan='starter',
        )
        db.session.add(abonnement)
        db.session.commit()

        from flask_jwt_extended import create_access_token
        token = create_access_token(
            identity=user.id,
            additional_claims={
                'username': user.username,
                'email': user.email,
                'role': user.role.value,
                'tenant_id': tenant.id,
                'tenant_slug': tenant.slug,
            }
        )
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        return headers, tenant.id, user.id, abonnement.id


def _papi_response(payment_link='https://pay.papi.mg/payment/abc123', notification_token='token-xyz', reference=None):
    ref = reference or f'SUB-1-1-{uuid.uuid4().hex[:8].upper()}'
    return {
        'data': {
            'amount': 15000.0,
            'currency': 'MGA',
            'linkCreationDateTime': 1723850012,
            'linkExpirationDateTime': 1723853612,
            'paymentLink': payment_link,
            'clientName': 'Test Tenant',
            'paymentReference': ref,
            'description': 'Abonnement starter - Test Tenant',
            'successUrl': f'http://localhost:5000/api/v1/papi/payment-result?status=success&reference={ref}',
            'failureUrl': f'http://localhost:5000/api/v1/papi/payment-result?status=failure&reference={ref}',
            'notificationUrl': 'http://localhost:5000/api/v1/papi/webhook',
            'payerEmail': 'test@example.com',
            'payerPhone': '+261340000000',
            'notificationToken': notification_token,
            'testReason': 'Integration test ERP',
            'isTestMode': True,
        }
    }


class TestPapiPaymentCreation:

    def test_create_payment_requires_auth(self, client, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        response = client.post(
            f'/api/v1/papi/payments/subscription/{sub_id}',
            json={'payment_method': 'MVOLA'},
        )
        assert response.status_code == 401

    def test_create_payment_success(self, client, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        mock_response = _papi_response()

        with patch('app.services.papi.client.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status.return_value = None

            response = client.post(
                f'/api/v1/papi/payments/subscription/{sub_id}',
                headers=headers,
                json={'payment_method': 'MVOLA', 'is_test_mode': True},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert 'payment_link' in data
        assert data['payment_link'] == mock_response['data']['paymentLink']
        assert data['payment']['provider'] == 'papi'
        assert data['payment']['payment_method'] == 'MVOLA'
        assert data['payment']['statut'] == 'en_attente'

    def test_create_payment_invalid_method(self, client, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        response = client.post(
            f'/api/v1/papi/payments/subscription/{sub_id}',
            headers=headers,
            json={'payment_method': 'INVALID_METHOD'},
        )
        assert response.status_code == 400

    def test_create_payment_subscription_not_found(self, client, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        response = client.post(
            '/api/v1/papi/payments/subscription/99999',
            headers=headers,
            json={'payment_method': 'MVOLA'},
        )
        assert response.status_code == 400

    def test_create_payment_tenant_mismatch(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers

        with app.app_context():
            other_slug = f'other-tenant-{uuid.uuid4().hex[:8]}'
            other_tenant = Tenant(
                nom='Other Tenant',
                slug=other_slug,
                statut=StatutTenant.ACTIF,
                plan='starter',
            )
            db.session.add(other_tenant)
            db.session.flush()

            other_user = Utilisateur(
                username='otheruser',
                email=f'other-{uuid.uuid4().hex[:8]}@example.com',
                password_hash=hash_password('password123'),
                role=Role.ADMIN,
                tenant_id=other_tenant.id,
                statut=StatutUtilisateur.ACTIF,
            )
            db.session.add(other_user)
            db.session.commit()

            from flask_jwt_extended import create_access_token
            other_token = create_access_token(
                identity=other_user.id,
                additional_claims={
                    'username': other_user.username,
                    'email': other_user.email,
                    'role': other_user.role.value,
                    'tenant_id': other_tenant.id,
                    'tenant_slug': other_tenant.slug,
                }
            )
            other_headers = {
                'Authorization': f'Bearer {other_token}',
                'Content-Type': 'application/json',
            }

        response = client.post(
            f'/api/v1/papi/payments/subscription/{sub_id}',
            headers=other_headers,
            json={'payment_method': 'MVOLA'},
        )
        assert response.status_code == 400

    def test_create_payment_amount_too_low(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        with app.app_context():
            abonnement = db.session.get(Abonnement, sub_id)
            abonnement.montant = 100.0
            db.session.commit()

        mock_response = _papi_response()
        with patch('app.services.papi.client.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status.return_value = None

            response = client.post(
                f'/api/v1/papi/payments/subscription/{sub_id}',
                headers=headers,
                json={'payment_method': 'MVOLA'},
            )
        assert response.status_code == 400


class TestPapiOfflinePayment:

    def test_create_offline_payment_success(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        response = client.post(
            f'/api/v1/papi/payments/subscription/{sub_id}',
            headers=headers,
            json={'payment_method': 'especes'},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['is_offline'] is True
        assert data['payment']['provider'] == 'manuel'
        assert data['payment']['payment_method'] == 'ESPECES'
        assert data['payment']['statut'] == 'en_attente'
        assert 'reference' in data and data['reference'].startswith('PAPIER-')
        assert data['instructions']

    def test_create_offline_payment_via_alias(self, client, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        response = client.post(
            f'/api/v1/papi/payments/subscription/{sub_id}',
            headers=headers,
            json={'payment_method': 'cheque'},
        )
        assert response.status_code == 200
        assert response.get_json()['payment']['payment_method'] == 'CHEQUE'

    def test_list_includes_offline_payments(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        create = client.post(
            f'/api/v1/papi/payments/subscription/{sub_id}',
            headers=headers,
            json={'payment_method': 'virement'},
        )
        assert create.status_code == 200

        response = client.get('/api/v1/papi/payments', headers=headers)
        assert response.status_code == 200
        payments = response.get_json()['payments']
        assert any(p['provider'] == 'manuel' for p in payments)


class TestPapiWebhook:

    def test_webhook_valid_success(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        with app.app_context():
            mock_response = _papi_response()
            reference = mock_response['data']['paymentReference']
            notification_token = mock_response['data']['notificationToken']

            with patch('app.services.papi.client.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = mock_response
                mock_post.return_value.raise_for_status.return_value = None

                create_resp = client.post(
                    f'/api/v1/papi/payments/subscription/{sub_id}',
                    headers=headers,
                    json={'payment_method': 'MVOLA', 'is_test_mode': True},
                )
            assert create_resp.status_code == 200

            paiement = Paiement.query.filter_by(external_reference=reference).first()
            paiement.notification_token = notification_token
            db.session.commit()

            webhook_payload = {
                'paymentStatus': 'SUCCESS',
                'paymentMethod': 'MVOLA',
                'currency': 'MGA',
                'amount': 15000,
                'fee': 500,
                'clientName': 'Test Tenant',
                'description': 'Abonnement starter - Test Tenant',
                'merchantPaymentReference': 'MERCHANT-0001',
                'paymentReference': reference,
                'notificationToken': notification_token,
                'message': 'Paiement effectué avec succès.',
                'payerEmail': 'test@example.com',
                'payerPhone': '+261340000000',
            }

            response = client.post(
                '/api/v1/papi/webhook',
                data=json.dumps(webhook_payload),
                content_type='application/json',
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'processed'
        assert data['payment_status'] == 'succes'

        with app.app_context():
            paiement = Paiement.query.filter_by(external_reference=reference).first()
            assert paiement.statut == StatutPaiement.SUCCESS

            abonnement = db.session.get(Abonnement, sub_id)
            assert abonnement.statut == StatutAbonnement.ACTIF

    def test_webhook_invalid_token(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        webhook_payload = {
            'paymentStatus': 'SUCCESS',
            'paymentMethod': 'MVOLA',
            'currency': 'MGA',
            'amount': 15000,
            'paymentReference': 'SUB-1-1-UNKNOWN',
            'notificationToken': 'wrong-token',
            'message': 'Paiement effectué avec succès.',
        }

        response = client.post(
            '/api/v1/papi/webhook',
            data=json.dumps(webhook_payload),
            content_type='application/json',
        )
        assert response.status_code == 403

    def test_webhook_duplicate_event(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        with app.app_context():
            mock_response = _papi_response()
            reference = mock_response['data']['paymentReference']
            notification_token = mock_response['data']['notificationToken']

            with patch('app.services.papi.client.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = mock_response
                mock_post.return_value.raise_for_status.return_value = None

                create_resp = client.post(
                    f'/api/v1/papi/payments/subscription/{sub_id}',
                    headers=headers,
                    json={'payment_method': 'MVOLA', 'is_test_mode': True},
                )
            assert create_resp.status_code == 200

            paiement = Paiement.query.filter_by(external_reference=reference).first()
            paiement.notification_token = notification_token
            db.session.commit()

            webhook_payload = {
                'paymentStatus': 'SUCCESS',
                'paymentMethod': 'MVOLA',
                'currency': 'MGA',
                'amount': 15000,
                'paymentReference': reference,
                'notificationToken': notification_token,
                'message': 'Paiement effectué avec succès.',
            }

            response1 = client.post(
                '/api/v1/papi/webhook',
                data=json.dumps(webhook_payload),
                content_type='application/json',
            )
            assert response1.status_code == 200

            response2 = client.post(
                '/api/v1/papi/webhook',
                data=json.dumps(webhook_payload),
                content_type='application/json',
            )
            assert response2.status_code == 200
            assert response2.get_json()['status'] == 'already_processed'

    def test_webhook_failed_payment(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        with app.app_context():
            mock_response = _papi_response()
            reference = mock_response['data']['paymentReference']
            notification_token = mock_response['data']['notificationToken']

            with patch('app.services.papi.client.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = mock_response
                mock_post.return_value.raise_for_status.return_value = None

                create_resp = client.post(
                    f'/api/v1/papi/payments/subscription/{sub_id}',
                    headers=headers,
                    json={'payment_method': 'MVOLA', 'is_test_mode': True},
                )
            assert create_resp.status_code == 200

            paiement = Paiement.query.filter_by(external_reference=reference).first()
            paiement.notification_token = notification_token
            db.session.commit()

            webhook_payload = {
                'paymentStatus': 'FAILED',
                'paymentMethod': 'MVOLA',
                'currency': 'MGA',
                'amount': 15000,
                'paymentReference': reference,
                'notificationToken': notification_token,
                'message': 'Paiement échoué.',
            }

            response = client.post(
                '/api/v1/papi/webhook',
                data=json.dumps(webhook_payload),
                content_type='application/json',
            )

        assert response.status_code == 200
        with app.app_context():
            paiement = Paiement.query.filter_by(external_reference=reference).first()
            assert paiement.statut == StatutPaiement.FAILED

            abonnement = db.session.get(Abonnement, sub_id)
            assert abonnement.statut != StatutAbonnement.ACTIF

    def test_webhook_missing_fields(self, client):
        response = client.post(
            '/api/v1/papi/webhook',
            data=json.dumps({'paymentStatus': 'SUCCESS'}),
            content_type='application/json',
        )
        assert response.status_code == 403


class TestPapiPaymentList:

    def test_list_papi_payments(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        with app.app_context():
            paiement = Paiement(
                tenant_id=tenant_id,
                subscription_id=sub_id,
                montant=15000.0,
                devise='MGA',
                statut=StatutPaiement.EN_ATTENTE,
                type=TypePaiement.ABONNEMENT,
                provider=ProviderPaiement.PAPI.value,
                payment_method='MVOLA',
                external_payment_id='https://pay.papi.mg/payment/abc123',
                external_reference='SUB-1-1-TEST123',
                reference='SUB-1-1-TEST123',
            )
            db.session.add(paiement)
            db.session.commit()

            response = client.get('/api/v1/papi/payments', headers=headers)

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['payments']) == 1
        assert data['payments'][0]['provider'] == 'papi'

    def test_list_papi_payments_empty(self, client, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        response = client.get('/api/v1/papi/payments', headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['payments'] == []


class TestIdempotence:

    def test_duplicate_create_returns_existing(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        mock_response = _papi_response()

        with patch('app.services.papi.client.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status.return_value = None

            response1 = client.post(
                f'/api/v1/papi/payments/subscription/{sub_id}',
                headers=headers,
                json={'payment_method': 'MVOLA', 'is_test_mode': True},
            )
            assert response1.status_code == 200

            response2 = client.post(
                f'/api/v1/papi/payments/subscription/{sub_id}',
                headers=headers,
                json={'payment_method': 'MVOLA', 'is_test_mode': True},
            )
            assert response2.status_code == 200

        with app.app_context():
            count = Paiement.query.filter_by(
                tenant_id=tenant_id,
                external_reference=mock_response['data']['paymentReference'],
                is_active=True,
            ).count()
            assert count == 1
