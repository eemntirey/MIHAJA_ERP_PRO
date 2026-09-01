
import hashlib
import hmac
import logging
from datetime import datetime

from app import db
from app.models.paiement import Paiement, StatutPaiement
from app.models.payment_event import PaymentEvent
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.tenant import Tenant, StatutTenant
from app.services.papi.errors import (
    PapiWebhookError,
    PapiDuplicateWebhookError,
    PapiInvalidStatusError,
)
from app.config.settings import Config

logger = logging.getLogger(__name__)


def _verify_webhook_signature(payload: dict, headers) -> bool:
    secret = getattr(Config, 'PAPI_WEBHOOK_SECRET', None)
    if not secret:
        logger.warning('PAPI_WEBHOOK_SECRET not configured; signature verification skipped')
        return True
    signature_headers = [
        headers.get('X-Papi-Signature'),
        headers.get('X-Hub-Signature-256'),
        headers.get('X-Webhook-Signature'),
        headers.get('X-Papi-Hub-Signature'),
    ]
    received_sig = next((s for s in signature_headers if s), None)
    if not received_sig:
        logger.error('Papi webhook missing signature header')
        return False
    raw_body = str(payload)
    expected = hmac.new(
        secret.encode('utf-8'),
        raw_body.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, received_sig):
        logger.error('Papi webhook signature mismatch')
        return False
    return True


def process_papi_webhook(payload: dict, headers=None) -> dict:
    """Process an incoming Papi webhook notification.

    Args:
        payload: The JSON body from Papi webhook.
        headers: HTTP headers for signature verification.

    Returns:
        Dict with processing result.

    Raises:
        PapiWebhookError: If webhook is invalid.
        PapiDuplicateWebhookError: If event already processed.
        PapiInvalidStatusError: If status is unexpected.
    """
    if headers is None:
        headers = {}

    if not _verify_webhook_signature(payload, headers):
        raise PapiWebhookError('Signature du webhook invalide')

    payment_reference = payload.get('paymentReference')
    notification_token = payload.get('notificationToken')
    payment_status = payload.get('paymentStatus')
    payment_method = payload.get('paymentMethod', '')
    currency = payload.get('currency', 'MGA')
    amount = payload.get('amount')
    fee = payload.get('fee', 0)
    client_name = payload.get('clientName', '')
    description = payload.get('description', '')
    merchant_reference = payload.get('merchantPaymentReference', '')
    message = payload.get('message', '')
    payer_email = payload.get('payerEmail', '')
    payer_phone = payload.get('payerPhone', '')

    logger.info(
        'Papi webhook received: reference=%s status=%s method=%s',
        payment_reference,
        payment_status,
        payment_method,
    )

    if not payment_reference or not notification_token:
        logger.error('Papi webhook missing required fields')
        raise PapiWebhookError('Champs requis manquants dans le webhook')

    if payment_status not in ('SUCCESS', 'PENDING', 'FAILED'):
        logger.error('Papi webhook invalid status: %s', payment_status)
        raise PapiInvalidStatusError(f"Statut de paiement invalide: {payment_status}")

    event_id = f"papi-{payment_reference}-{notification_token}"
    existing_event = PaymentEvent.query.filter_by(event_id=event_id).first()
    if existing_event and existing_event.processed:
        logger.info('Papi webhook already processed: event_id=%s', event_id)
        return {
            'status': 'already_processed',
            'event_id': event_id,
        }

    paiement = Paiement.query.filter_by(
        external_reference=payment_reference,
        is_active=True,
    ).first()

    if not paiement:
        logger.error('Papi webhook for unknown payment reference: %s', payment_reference)
        raise PapiWebhookError('Paiement introuvable')

    if paiement.notification_token and paiement.notification_token != notification_token:
        logger.error(
            'Papi webhook token mismatch: stored=%s received=%s',
            paiement.notification_token,
            notification_token,
        )
        raise PapiWebhookError('Token de notification invalide')

    if paiement.tenant_id:
        tenant = db.session.get(Tenant, paiement.tenant_id)
        if not tenant or not tenant.is_active or tenant.statut in (StatutTenant.INACTIF, StatutTenant.BLOQUE):
            logger.error('Papi webhook for inactive tenant: tenant_id=%s', paiement.tenant_id)
            raise PapiWebhookError('Tenant inactif ou bloque')

    if amount is not None and float(amount) != float(paiement.montant or 0):
        logger.error(
            'Papi webhook amount mismatch: expected=%s received=%s',
            paiement.montant,
            amount,
        )
        raise PapiWebhookError('Montant de paiement invalide')

    if currency != (paiement.devise or 'MGA'):
        logger.error(
            'Papi webhook currency mismatch: expected=%s received=%s',
            paiement.devise,
            currency,
        )
        raise PapiWebhookError('Devise de paiement invalide')

    if not existing_event:
        payment_event = PaymentEvent(
            payment_id=paiement.id,
            event_id=event_id,
            event_type=payment_status,
            payload=payload,
            signature=notification_token,
            processed=False,
        )
        db.session.add(payment_event)
        db.session.flush()
    else:
        payment_event = existing_event
        payment_event.payload = payload
        payment_event.received_at = datetime.utcnow()

    old_status = paiement.statut
    new_status = old_status

    if payment_status == 'SUCCESS':
        if paiement.statut != StatutPaiement.SUCCESS:
            paiement.statut = StatutPaiement.SUCCESS
            paiement.date_paiement = datetime.utcnow()
            new_status = StatutPaiement.SUCCESS

        if paiement.subscription_id:
            subscription = db.session.get(Abonnement, paiement.subscription_id)
            if subscription and subscription.statut != StatutAbonnement.ACTIF:
                subscription.statut = StatutAbonnement.ACTIF
                if not subscription.date_debut:
                    subscription.date_debut = datetime.utcnow()
                if not subscription.date_fin:
                    from datetime import timedelta
                    subscription.date_fin = datetime.utcnow() + timedelta(days=30)
                subscription.methode_paiement = paiement.payment_method
                subscription.reference_paiement = paiement.external_reference
                db.session.add(subscription)

                if subscription.tenant_id:
                    tenant = db.session.get(Tenant, subscription.tenant_id)
                    if tenant and tenant.statut != StatutTenant.ACTIF:
                        tenant.statut = StatutTenant.ACTIF
                        tenant.date_abonnement = datetime.utcnow()
                        db.session.add(tenant)

    elif payment_status == 'FAILED':
        if paiement.statut != StatutPaiement.FAILED:
            paiement.statut = StatutPaiement.FAILED
            new_status = StatutPaiement.FAILED

    elif payment_status == 'PENDING':
        if paiement.statut == StatutPaiement.PENDING:
            paiement.statut = StatutPaiement.PROCESSING
            new_status = StatutPaiement.PROCESSING

    payment_event.processed = True
    payment_event.processed_at = datetime.utcnow()
    db.session.commit()

    logger.info(
        'Papi webhook processed: paiement_id=%s old_status=%s new_status=%s',
        paiement.id,
        old_status.value if hasattr(old_status, 'value') else old_status,
        new_status.value if hasattr(new_status, 'value') else new_status,
    )

    return {
        'status': 'processed',
        'event_id': event_id,
        'payment_id': paiement.id,
        'payment_status': new_status.value if hasattr(new_status, 'value') else new_status,
    }
