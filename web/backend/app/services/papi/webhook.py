
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal

from app import db
from app.models.paiement import Paiement, StatutPaiement
from app.models.payment_event import PaymentEvent
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.tenant import Tenant, StatutTenant
from app.services.commande_papi_service import parse_papi_reference
from app.services.papi.errors import (
    PapiWebhookError,
    PapiDuplicateWebhookError,
    PapiInvalidStatusError,
)
from app.services.tenant_papi_service import get_webhook_secret_for_tenant
from app.models.commande_client import CommandeClient, StatutCommande
from app.config.settings import Config
from app.security.plans import get_plan_duration_days, is_unlimited

logger = logging.getLogger(__name__)


def _resolve_webhook_secret(payload: dict) -> str:
    """Détermine le secret webhook à utiliser.

    Stratégie :
    - Si la référence porte un tenant_id (CMD-<tenant>-... ou SUB-<tenant>-...),
      on tente d'utiliser le secret webhook du tenant.
    - Sinon (abonnements legacy, références non conformes), fallback sur
      le secret plateforme ``Config.PAPI_WEBHOOK_SECRET``.
    """
    # Dans une notification Papi, paymentReference est la référence
    # de la tentative Papi ; merchantPaymentReference est notre référence
    # métier envoyée lors de la création du lien.
    reference = (
        (payload or {}).get('merchantPaymentReference')
        or (payload or {}).get('paymentReference')
        or ''
    )
    parsed = parse_papi_reference(reference)
    if parsed and parsed.get('tenant_id'):
        tenant = db.session.get(Tenant, parsed['tenant_id'])
        tenant_secret = get_webhook_secret_for_tenant(tenant) if tenant else None
        if tenant_secret:
            return tenant_secret
    return getattr(Config, 'PAPI_WEBHOOK_SECRET', None) or ''


def _verify_webhook_signature(payload: dict, headers, raw_body=None) -> bool:
    """Vérifie la signature Papi selon le format officiel t=...,v1=....

    Papi signe les octets bruts avec HMAC-SHA256 sur timestamp.raw_body
    et impose une tolérance de 300 secondes pour limiter les rejeux.
    """
    secret = _resolve_webhook_secret(payload)
    if not secret:
        logger.error('Aucun secret webhook Papi disponible; webhook refuse')
        return False

    header = headers.get('X-Papi-Signature') if headers else None
    if not header:
        logger.error('Papi webhook missing X-Papi-Signature header')
        return False

    values = {}
    try:
        for part in header.split(','):
            key, value = part.strip().split('=', 1)
            values[key] = value
    except ValueError:
        logger.error('Papi webhook signature header malformed')
        return False

    timestamp_raw = values.get('t')
    received_sig = values.get('v1')
    if not timestamp_raw or not received_sig:
        logger.error('Papi webhook signature missing timestamp or v1')
        return False

    try:
        timestamp = int(timestamp_raw)
    except (TypeError, ValueError):
        logger.error('Papi webhook invalid signature timestamp')
        return False

    now = int(time.time())
    if abs(now - timestamp) > 300:
        logger.error('Papi webhook timestamp outside tolerance window')
        return False

    if raw_body is None:
        raw_body = b''
    raw_body_bytes = raw_body if isinstance(raw_body, bytes) else str(raw_body).encode('utf-8')
    signed_message = str(timestamp).encode('ascii') + b'.' + raw_body_bytes
    expected = hmac.new(
        secret.encode('utf-8'),
        signed_message,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, received_sig):
        logger.error('Papi webhook signature mismatch')
        return False
    return True

def process_papi_webhook(payload: dict, headers=None, raw_body=None) -> dict:
    """Process an incoming Papi webhook notification.

    Args:
        payload: The JSON body from Papi webhook.
        headers: HTTP headers for signature verification.
        raw_body: Raw HTTP request body (bytes/str) as received. When
            provided, the HMAC signature is verified over these exact
            bytes (standard webhook practice) instead of str(payload).

    Returns:
        Dict with processing result.

    Raises:
        PapiWebhookError: If webhook is invalid.
        PapiDuplicateWebhookError: If event already processed.
        PapiInvalidStatusError: If status is unexpected.
    """
    if headers is None:
        headers = {}

    if not _verify_webhook_signature(payload, headers, raw_body=raw_body):
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

    # Papi distingue la référence marchande de la référence de paiement :
    # merchantPaymentReference correspond à notre external_reference ;
    # paymentReference est l'UUID de la tentative côté Papi.
    merchant_ref = merchant_reference or payment_reference
    event_ref = payment_reference or merchant_ref
    event_id = f"papi-{merchant_ref}-{event_ref}-{notification_token}"
    existing_event = PaymentEvent.query.filter_by(event_id=event_id).first()
    if existing_event and existing_event.processed:
        logger.info('Papi webhook already processed: event_id=%s', event_id)
        return {
            'status': 'already_processed',
            'event_id': event_id,
        }

    # Priorité à la référence marchande officielle. Le fallback sur
    # paymentReference conserve la compatibilité avec les callbacks legacy
    # émis avant l'alignement Papi actuel.
    paiement = Paiement.query.filter_by(
        external_reference=merchant_ref,
        is_active=True,
    ).first()
    if not paiement and merchant_ref != payment_reference:
        paiement = Paiement.query.filter_by(
            external_reference=payment_reference,
            is_active=True,
        ).first()

    if not paiement:
        logger.error('Papi webhook for unknown payment reference: %s', payment_reference)
        raise PapiWebhookError('Paiement introuvable')

    stored_notification_token = getattr(paiement, 'notification_token', None)
    try:
        metadata = json.loads(paiement.payment_metadata or '{}')
    except (TypeError, ValueError):
        metadata = {}
    stored_notification_token = stored_notification_token or metadata.get('notification_token')
    stored_merchant_reference = metadata.get('merchant_payment_reference')
    if stored_merchant_reference and stored_merchant_reference != merchant_ref:
        logger.error('Papi merchant reference mismatch for paiement_id=%s', paiement.id)
        raise PapiWebhookError('Référence marchande invalide')
    if not stored_notification_token:
        logger.error('Papi webhook token absent for paiement_id=%s', paiement.id)
        raise PapiWebhookError('Token de notification non enregistré')
    if stored_notification_token != notification_token:
        logger.error(
            'Papi webhook token mismatch: stored=%s received=%s',
            stored_notification_token,
            notification_token,
        )
        raise PapiWebhookError('Token de notification invalide')

    if paiement.tenant_id:
        tenant = db.session.get(Tenant, paiement.tenant_id)
        if not tenant or not tenant.is_active or tenant.statut in (StatutTenant.INACTIF, StatutTenant.BLOQUE):
            logger.error('Papi webhook for inactive tenant: tenant_id=%s', paiement.tenant_id)
            raise PapiWebhookError('Tenant inactif ou bloque')

    if amount is not None:
        try:
            received_amount = Decimal(str(amount)).quantize(Decimal('0.01'))
            expected_amount = Decimal(str(paiement.montant or 0)).quantize(Decimal('0.01'))
        except Exception:
            logger.error('Papi webhook amount is not numeric: %r', amount)
            raise PapiWebhookError('Montant de paiement invalide')
        if received_amount != expected_amount:
            logger.error(
                'Papi webhook amount mismatch: expected=%s received=%s',
                expected_amount,
                received_amount,
            )
            raise PapiWebhookError('Montant de paiement invalide')

    if str(currency or '').upper() != str(paiement.devise or 'MGA').upper():
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
            if subscription:
                now = datetime.utcnow()
                was_active = subscription.statut == StatutAbonnement.ACTIF
                subscription.statut = StatutAbonnement.ACTIF
                if not subscription.date_debut:
                    subscription.date_debut = now
                if not subscription.date_fin or subscription.date_fin <= now:
                    duration = get_plan_duration_days(subscription.plan)
                    subscription.date_fin = (
                        now + timedelta(days=365 * 99)
                        if is_unlimited(duration)
                        else now + timedelta(days=duration)
                    )
                subscription.methode_paiement = paiement.payment_method
                subscription.reference_paiement = paiement.external_reference
                db.session.add(subscription)

                if subscription.tenant_id:
                    tenant = db.session.get(Tenant, subscription.tenant_id)
                    if tenant:
                        tenant.statut = StatutTenant.ACTIF
                        tenant.is_active = True
                        tenant.plan = subscription.plan
                        if not was_active:
                            tenant.date_abonnement = now
                        db.session.add(tenant)

        if paiement.commande_client_id:
            commande = db.session.get(CommandeClient, paiement.commande_client_id)
            if commande and commande.statut != StatutCommande.LIVREE:
                if commande.statut == StatutCommande.EN_ATTENTE:
                    commande.statut = StatutCommande.CONFIRMEE
                db.session.add(commande)

    elif payment_status == 'FAILED':
        if paiement.statut != StatutPaiement.FAILED:
            paiement.statut = StatutPaiement.FAILED
            new_status = StatutPaiement.FAILED

    elif payment_status == 'PENDING':
        # Papi peut envoyer PENDING alors que le paiement local vient d'être
        # créé en EN_ATTENTE. L'état canonique local devient PROCESSING.
        if paiement.statut in (StatutPaiement.EN_ATTENTE, StatutPaiement.PENDING):
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
