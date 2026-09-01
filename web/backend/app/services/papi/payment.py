
import uuid
import logging
from datetime import datetime

from app import db
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement, ProviderPaiement
from app.models.tenant import Tenant
from app.models.utilisateur import Utilisateur
from app.security.tenant import get_current_tenant_id, get_current_tenant
from app.services.papi.client import PapiClient
from app.services.papi.errors import PapiError, PapiAuthError, PapiValidationError, PapiUnavailableError
from app.config.settings import Config

logger = logging.getLogger(__name__)

PROVIDER_METHOD_MAP = {
    'MVOLA': 'MVOLA',
    'ORANGE_MONEY': 'ORANGE_MONEY',
    'ARTEL_MONEY': 'AIRTEL_MONEY',
    'BRED': 'VISA',
}


def _build_papi_payload(
    subscription: Abonnement,
    tenant: Tenant,
    user: Utilisateur,
    notification_token: str,
    payment_method: str,
    is_test_mode: bool = False,
) -> dict:
    """Build the Papi payment link creation payload."""
    reference = f"SUB-{tenant.id}-{subscription.id}-{uuid.uuid4().hex[:8].upper()}"

    provider = payment_method.upper()
    if provider not in ('MVOLA', 'ORANGE_MONEY', 'ARTEL_MONEY', 'BRED'):
        raise PapiValidationError(f"Mode de paiement invalide: {payment_method}")

    success_url = (
        f"{Config.PAPI_CALLBACK_URL}/../payment-result?"
        f"status=success&reference={reference}"
    )
    failure_url = (
        f"{Config.PAPI_CALLBACK_URL}/../payment-result?"
        f"status=failure&reference={reference}"
    )

    payload = {
        'amount': float(subscription.montant),
        'clientName': tenant.nom,
        'reference': reference,
        'description': f"Abonnement {subscription.plan} - {tenant.nom}",
        'successUrl': success_url,
        'failureUrl': failure_url,
        'notificationUrl': Config.PAPI_CALLBACK_URL,
        'validDuration': 60,
        'provider': provider,
        'payerEmail': tenant.email_contact or user.email,
        'payerPhone': tenant.telephone or user.mobile,
        'isTestMode': is_test_mode,
    }
    if is_test_mode:
        payload['testReason'] = 'Integration test ERP'

    if provider == 'BRED':
        payload['provider'] = 'BRED'

    return payload


def create_subscription_payment(
    subscription_id: int,
    payment_method: str,
    is_test_mode: bool = False,
    tenant_id: int = None,
) -> dict:
    """Create a Papi payment link for a subscription.

    Args:
        subscription_id: The subscription to pay.
        payment_method: One of MVOLA, ORANGE_MONEY, ARTEL_MONEY, BRED.
        is_test_mode: Whether to use Papi test mode.
        tenant_id: Tenant ID (optional, falls back to current request tenant).

    Returns:
        Dict with payment data including payment_link, payment, subscription.

    Raises:
        ValueError: If subscription/tenant not found or validation fails.
        PapiError: If Papi API call fails.
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise ValueError("Aucun tenant associe")

    tenant = None
    try:
        tenant = get_current_tenant()
    except Exception:
        pass
    
    if not tenant:
        from app.models.tenant import Tenant
        tenant = db.session.get(Tenant, tenant_id)

    subscription = db.session.get(Abonnement, subscription_id)
    if not subscription:
        raise ValueError("Abonnement non trouve")

    if subscription.tenant_id != tenant_id:
        raise ValueError("Acces refuse a cet abonnement")

    user_id = None
    try:
        from flask_jwt_extended import get_jwt_identity
        user_id = get_jwt_identity()
    except Exception:
        pass

    user = None
    if user_id:
        user = db.session.get(Utilisateur, user_id)

    if not subscription.montant or float(subscription.montant) < 300:
        raise ValueError("Le montant de l'abonnement est inferieur au minimum requis (300 MGA)")

    if not Config.PAPI_API_KEY:
        raise ValueError("Papi n'est pas configure: PAPI_API_KEY manquant")

    papi_client = PapiClient(
        api_url=Config.PAPI_API_URL,
        api_key=Config.PAPI_API_KEY,
        environment=Config.PAPI_ENVIRONMENT,
    )

    payload = _build_papi_payload(subscription, tenant, user, '', payment_method, is_test_mode)

    try:
        papi_data = papi_client.create_payment_link(payload)
    except PapiAuthError as exc:
        logger.error("Papi auth error: %s", exc)
        raise ValueError("Authentification Papi invalide") from exc
    except PapiValidationError as exc:
        logger.error("Papi validation error: %s", exc)
        raise ValueError(str(exc)) from exc
    except PapiUnavailableError as exc:
        logger.error("Papi unavailable: %s", exc)
        raise ValueError("Service de paiement indisponible, veuillez reessayer") from exc
    except PapiError as exc:
        logger.error("Papi error: %s", exc)
        raise ValueError(str(exc)) from exc

    external_reference = papi_data.get('paymentReference', payload['reference'])
    notification_token = papi_data.get('notificationToken', '')

    existing_payment = Paiement.query.filter_by(
        tenant_id=tenant_id,
        external_reference=external_reference,
        is_active=True,
    ).first()

    if existing_payment:
        logger.info(
            "Idempotent payment found for reference=%s, returning existing",
            external_reference,
        )
        return {
            'payment_link': existing_payment.external_payment_id,
            'payment': existing_payment.to_dict(),
            'subscription': subscription.to_dict(),
        }

    payment_method_db = PROVIDER_METHOD_MAP.get(payment_method.upper(), payment_method.upper())

    paiement = Paiement(
        tenant_id=tenant_id,
        subscription_id=subscription.id,
        montant=subscription.montant,
        devise=subscription.devise or 'MGA',
        statut=StatutPaiement.EN_ATTENTE,
        type=TypePaiement.ABONNEMENT,
        provider=ProviderPaiement.PAPI.value,
        payment_method=payment_method_db,
        external_payment_id=papi_data.get('paymentLink', ''),
        external_reference=external_reference,
        reference=external_reference,
        notes=f"Paiement abonnement {subscription.plan} via Papi",
    )

    db.session.add(paiement)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Echec commit Paiement Papi: ref=%s", external_reference)
        raise

    logger.info(
        "Papi payment created: paiement_id=%s reference=%s",
        paiement.id,
        external_reference,
    )

    return {
        'payment_link': papi_data.get('paymentLink', ''),
        'payment': paiement.to_dict(),
        'subscription': subscription.to_dict(),
    }


PAPER_METHODS = ('ESPECES', 'VIREMENT', 'CHEQUE')
ELECTRONIC_METHODS = ('MVOLA', 'ORANGE_MONEY', 'ARTEL_MONEY', 'BRED')

METHOD_ALIASES = {
    'mvola': 'MVOLA',
    'orange_money': 'ORANGE_MONEY',
    'orange money': 'ORANGE_MONEY',
    'airtel_money': 'ARTEL_MONEY',
    'airtel money': 'ARTEL_MONEY',
    'bred': 'BRED',
    'especes': 'ESPECES',
    'espèces': 'ESPECES',
    'cash': 'ESPECES',
    'virement': 'VIREMENT',
    'bank_transfer': 'VIREMENT',
    'cheque': 'CHEQUE',
    'chèque': 'CHEQUE',
    'check': 'CHEQUE',
}


def normalize_payment_method(payment_method):
    raw = (payment_method or '').strip()
    if not raw:
        return None
    return METHOD_ALIASES.get(raw.lower(), raw.upper())


def resolve_payment_provider(methode_paiement):
    method = normalize_payment_method(methode_paiement)
    if not method:
        return 'especes', 'especes'
    if method in ELECTRONIC_METHODS:
        return 'papi', PROVIDER_METHOD_MAP.get(method, method)
    if method in PAPER_METHODS:
        return 'manuel', method
    return 'especes', method

PAPER_INSTRUCTIONS = {
    'ESPECES': (
        "Rendez-vous à notre agence avec cette référence et le montant en espèces. "
        "Le paiement est validé par un responsable après encaissement au guichet."
    ),
    'VIREMENT': (
        "Effectuez un virement bancaire vers le compte de l'entreprise en indiquant "
        "impérativement cette référence dans le libellé. Le paiement est confirmé après réception."
    ),
    'CHEQUE': (
        "Émettez un chèque à l'ordre de l'entreprise en indiquant cette référence au dos. "
        "Le paiement est validé à l'encaissement du chèque."
    ),
}


def create_subscription_offline_payment(
    subscription_id: int,
    payment_method: str,
    tenant_id: int = None,
) -> dict:
    """Create an offline (paper) payment record for a subscription.

    Handles espèces / virement / chèque. No external Papi gateway is used:
    a payment reference is generated and the record stays EN_ATTENTE until an
    administrator confirms the deposit.

    Returns:
        Dict with is_offline=True, payment, subscription, reference, instructions.
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise ValueError("Aucun tenant associe")

    tenant = None
    try:
        tenant = get_current_tenant()
    except Exception:
        pass

    if not tenant:
        tenant = db.session.get(Tenant, tenant_id)

    subscription = db.session.get(Abonnement, subscription_id)
    if not subscription:
        raise ValueError("Abonnement non trouve")

    if subscription.tenant_id != tenant_id:
        raise ValueError("Acces refuse a cet abonnement")

    if not subscription.montant or float(subscription.montant) < 300:
        raise ValueError("Le montant de l'abonnement est inferieur au minimum requis (300 MGA)")

    payment_method = (payment_method or '').upper()
    if payment_method not in PAPER_METHODS:
        raise ValueError("Mode de paiement papier invalide")

    reference = f"PAPIER-{tenant.id}-{subscription.id}-{uuid.uuid4().hex[:8].upper()}"

    existing_payment = Paiement.query.filter_by(
        tenant_id=tenant_id,
        external_reference=reference,
        is_active=True,
    ).first()

    if existing_payment:
        return {
            'is_offline': True,
            'payment': existing_payment.to_dict(),
            'subscription': subscription.to_dict(),
            'reference': existing_payment.reference,
            'instructions': PAPER_INSTRUCTIONS.get(payment_method, ''),
        }

    paiement = Paiement(
        tenant_id=tenant_id,
        subscription_id=subscription.id,
        montant=subscription.montant,
        devise=subscription.devise or 'MGA',
        statut=StatutPaiement.EN_ATTENTE,
        type=TypePaiement.ABONNEMENT,
        provider='manuel',
        payment_method=payment_method,
        reference=reference,
        external_reference=reference,
        notes=f"Paiement abonnement {subscription.plan} hors ligne ({payment_method})",
    )

    db.session.add(paiement)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Echec commit Paiement hors-ligne: ref=%s", reference)
        raise

    logger.info(
        "Offline payment created: paiement_id=%s reference=%s method=%s",
        paiement.id,
        reference,
        payment_method,
    )

    return {
        'is_offline': True,
        'payment': paiement.to_dict(),
        'subscription': subscription.to_dict(),
        'reference': reference,
        'instructions': PAPER_INSTRUCTIONS.get(payment_method, ''),
    }
