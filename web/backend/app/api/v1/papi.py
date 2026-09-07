import os

from flask import request, current_app
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.utilisateur import Utilisateur
from app.models.paiement import Paiement
from app.models.abonnement import Abonnement
from app.security.tenant import tenant_required, get_current_tenant_id
from app.services.papi.payment import (
    create_subscription_payment,
    create_subscription_offline_payment,
    PAPER_METHODS,
    ELECTRONIC_METHODS,
    METHOD_ALIASES,
    normalize_payment_method,
)
from app.config.settings import Config
from app.services.papi.webhook import process_papi_webhook
from app.services.papi.errors import (
    PapiError,
    PapiAuthError,
    PapiValidationError,
    PapiWebhookError,
    PapiDuplicateWebhookError,
    PapiInvalidStatusError,
)

ns = Namespace('papi', description='Intégration Papi (paiements en ligne et hors ligne)')

VALID_METHODS = ELECTRONIC_METHODS + PAPER_METHODS

PRODUCTION_ENVIRONMENTS = {'production', 'prod', 'live'}
ALLOW_TEST_MODE_KEY = 'PAPI_ALLOW_TEST_MODE'


def _is_production_environment():
    env = (Config.PAPI_ENVIRONMENT or '').lower()
    flask_env = (os.getenv('FLASK_ENV') or '').lower()
    debug = current_app.config.get('DEBUG', False)
    testing = current_app.config.get('TESTING', False)
    if testing:
        return False
    if debug and flask_env not in ('production', 'prod'):
        return False
    if env in PRODUCTION_ENVIRONMENTS:
        return True
    if flask_env in ('production', 'prod'):
        return True
    return False


def _resolve_is_test_mode(data):
    """Determine is_test_mode.

    Production rule: never honor client-supplied ``is_test_mode``. Even if
    the gateway is configured against a sandbox, real payments must go
    through ``isTestMode=false`` in production.
    """
    if _is_production_environment():
        return False

    testing = current_app.config.get('TESTING', False)
    env_value = str(os.getenv(ALLOW_TEST_MODE_KEY, '')).lower()
    if testing:
        # In test runs default to "client choice allowed" so existing
        # integration tests keep working.
        if env_value in ('0', 'false', 'no'):
            return False
        return bool(data.get('is_test_mode', False))

    if env_value not in ('1', 'true', 'yes'):
        return False

    return bool(data.get('is_test_mode', False))


def _get_tenant_id_from_jwt():
    claims = get_jwt() or {}
    return claims.get('tenant_id')


@ns.route('/payments/subscription/<int:subscription_id>')
class CreatePapiPayment(Resource):

    @jwt_required()
    def post(self, subscription_id):
        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401

        data = request.get_json() or {}
        payment_method = normalize_payment_method(data.get('payment_method', 'MVOLA'))
        is_test_mode = _resolve_is_test_mode(data)

        if not payment_method or payment_method not in VALID_METHODS:
            return {
                'message': f"Mode de paiement invalide. Choisissez parmi: {', '.join(VALID_METHODS)}"
            }, 400

        try:
            if payment_method in PAPER_METHODS:
                result = create_subscription_offline_payment(
                    subscription_id=subscription_id,
                    payment_method=payment_method,
                    tenant_id=tenant_id,
                )
            else:
                result = create_subscription_payment(
                    subscription_id=subscription_id,
                    payment_method=payment_method,
                    is_test_mode=is_test_mode,
                    tenant_id=tenant_id,
                )
            return result, 200
        except ValueError as exc:
            current_app.logger.warning('Papi payment creation validation error: %s', exc)
            return {'message': str(exc)}, 400
        except PapiError as exc:
            current_app.logger.error('Papi payment creation error: %s', exc)
            return {'message': 'Erreur du service de paiement'}, 502
        except Exception as exc:
            current_app.logger.exception('Unexpected error during Papi payment creation')
            return {'message': 'Erreur interne du service de paiement'}, 500


@ns.route('/payments')
class ListPapiPayments(Resource):

    @jwt_required()
    def get(self):
        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401

        query = Paiement.query.filter(
            Paiement.tenant_id == tenant_id,
            Paiement.is_active == True,
            Paiement.provider.in_(['papi', 'manuel']),
        )
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        paginated = query.order_by(Paiement.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            'payments': [p.to_dict() for p in paginated.items],
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
        }, 200


@ns.route('/payments/<int:id>')
class PapiPaymentDetail(Resource):

    @jwt_required()
    def get(self, id):
        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401

        payment = Paiement.query.filter_by(
            id=id,
            tenant_id=tenant_id,
            is_active=True,
            provider='papi',
        ).first()

        if not payment:
            return {'message': 'Paiement non trouve'}, 404

        return payment.to_dict(), 200


@ns.route('/webhook')
class PapiWebhook(Resource):

    def post(self):
        payload = request.get_json() or {}
        current_app.logger.info(
            'Papi webhook received: %s',
            {k: v for k, v in payload.items() if k not in ('payload',)}
        )

        try:
            result = process_papi_webhook(payload, headers=dict(request.headers))
            status_code = 200
            if result.get('status') == 'already_processed':
                status_code = 200
            return result, status_code
        except PapiDuplicateWebhookError as exc:
            current_app.logger.info('Papi duplicate webhook: %s', exc)
            return {'status': 'already_processed'}, 200
        except PapiWebhookError as exc:
            current_app.logger.warning('Papi webhook validation error: %s', exc)
            return {'message': str(exc)}, 403
        except PapiInvalidStatusError as exc:
            current_app.logger.warning('Papi webhook invalid status: %s', exc)
            return {'message': str(exc)}, 400
        except Exception as exc:
            current_app.logger.exception('Unexpected error processing Papi webhook')
            return {'message': 'Erreur interne du webhook'}, 500
