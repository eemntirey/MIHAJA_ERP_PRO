"""Paiements Papi pour les commandes de la vitrine publique.

Le client qui commande sur la vitrine paie via le compte marchand Papi
**du tenant** (pas de MIHAJA). Cette couche construit le payload adapté,
crée la ligne ``Paiement`` liée à ``CommandeClient`` (via
``commande_client_id``) et applique la clé du tenant.

Le webhook Papi reçoit ``paymentReference`` au format ``CMD-<tenant>-<cmd>-<uuid>``
et retrouve le tenant par parsing pour vérifier la signature HMAC avec
la bonne clé.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Optional

from flask import current_app

from app import db
from app.models.commande_client import CommandeClient
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.tenant import Tenant
from app.services.papi.errors import (
    PapiAuthError,
    PapiError,
    PapiUnavailableError,
    PapiValidationError,
)
from app.services.tenant_papi_service import (
    TenantPapiConfigError,
    get_papi_client_for_tenant,
)
from app.config.settings import Config

logger = logging.getLogger(__name__)


# On garde la même liste de méthodes électroniques que pour les abonnements,
# la vitrine applique exactement les mêmes opérateurs.
ELECTRONIC_METHODS = ('MVOLA', 'ORANGE_MONEY', 'ARTEL_MONEY', 'BRED')

PROVIDER_METHOD_MAP = {
    'MVOLA': 'MVOLA',
    'ORANGE_MONEY': 'ORANGE_MONEY',
    'ARTEL_MONEY': 'AIRTEL_MONEY',
    'BRED': 'VISA',
}


# Format interne des références Papi pour les commandes vitrine.
CMD_REFERENCE_RE = re.compile(r'^CMD-(\d+)-(\d+)-[A-Z0-9]{1,16}$')
SUB_REFERENCE_RE = re.compile(r'^SUB-(\d+)-(\d+)-[A-Z0-9]{1,16}$')


def parse_papi_reference(reference: str) -> Optional[dict]:
    """Décode une référence Papi pour identifier tenant_id + type + id.

    Retourne ``None`` si le format est inconnu.
    """
    if not reference:
        return None
    m = CMD_REFERENCE_RE.match(reference)
    if m:
        return {
            'kind': 'commande',
            'tenant_id': int(m.group(1)),
            'entity_id': int(m.group(2)),
        }
    m = SUB_REFERENCE_RE.match(reference)
    if m:
        return {
            'kind': 'abonnement',
            'tenant_id': int(m.group(1)),
            'entity_id': int(m.group(2)),
        }
    return None


class CommandePapiError(ValueError):
    """Erreur métier lors d'un paiement Papi d'une commande vitrine."""


def _build_payload(
    commande: CommandeClient,
    tenant: Tenant,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    payment_method: str,
    notification_token: str,
    is_test_mode: bool,
) -> dict:
    reference = (
        f"CMD-{tenant.id}-{commande.id}-{uuid.uuid4().hex[:8].upper()}"
    )
    provider = payment_method.upper()
    if provider not in ELECTRONIC_METHODS:
        raise CommandePapiError(
            f"Mode de paiement invalide: {payment_method}"
        )

    callback_base = Config.PAPI_CALLBACK_URL or ''
    # URLs de retour : on s'appuie sur la route frontend /order-tracking/<ref>
    frontend_base = (Config.PAPI_CALLBACK_URL or '').rstrip('/')
    success_url = (
        f"{Config.PAPI_CALLBACK_URL}/../order-tracking/{commande.reference}"
        if Config.PAPI_CALLBACK_URL
        else ''
    )
    failure_url = success_url

    payload = {
        'amount': float(commande.total_ttc or 0),
        'clientName': customer_name or tenant.nom,
        'reference': reference,
        'description': (
            f"Commande {commande.reference} - {tenant.nom}"
        ),
        'successUrl': success_url,
        'failureUrl': failure_url,
        'notificationUrl': Config.PAPI_CALLBACK_URL,
        'validDuration': 60,
        'provider': PROVIDER_METHOD_MAP.get(provider, provider),
        'payerEmail': customer_email or tenant.email_contact,
        'payerPhone': customer_phone or tenant.telephone,
        'isTestMode': is_test_mode,
    }
    if is_test_mode:
        payload['testReason'] = 'Vitrine ERP test'
    return payload, reference


def create_commande_papi_payment(
    commande_id: int,
    payment_method: str,
    customer_name: str,
    customer_email: str,
    customer_phone: str = '',
    is_test_mode: bool = False,
) -> dict:
    """Crée un lien de paiement Papi (clé du tenant) pour une commande vitrine.

    Crée (ou réutilise pour idempotence) un Paiement lié à la CommandeClient.
    """
    commande = db.session.get(CommandeClient, commande_id)
    if not commande or not commande.is_active:
        raise CommandePapiError("Commande introuvable")

    tenant = db.session.get(Tenant, commande.tenant_id)
    if not tenant:
        raise CommandePapiError("Tenant introuvable")

    if not tenant.has_papi_configured():
        raise CommandePapiError(
            "Ce vendeur n'a pas configuré son compte Papi marchand. "
            "Veuillez choisir un autre mode de paiement."
        )

    if not tenant.vitrine_enabled:
        raise CommandePapiError(
            "Le paiement en ligne n'est pas disponible pour ce vendeur."
        )

    try:
        papi_client = get_papi_client_for_tenant(tenant)
    except TenantPapiConfigError as exc:
        raise CommandePapiError(str(exc)) from exc

    if not papi_client:
        raise CommandePapiError("Compte marchand Papi non configuré.")

    method_normalized = (payment_method or '').upper()
    if method_normalized not in ELECTRONIC_METHODS:
        raise CommandePapiError(
            f"Mode de paiement invalide: {payment_method}"
        )

    payload, reference = _build_payload(
        commande,
        tenant,
        customer_name,
        customer_email,
        customer_phone,
        method_normalized,
        '',
        is_test_mode,
    )

    try:
        papi_data = papi_client.create_payment_link(payload)
    except PapiAuthError as exc:
        logger.error(
            'Papi auth error for tenant_id=%s: %s', tenant.id, exc
        )
        raise CommandePapiError(
            "Le vendeur n'a pas pu encaisser le paiement (authentification Papi)."
        ) from exc
    except PapiValidationError as exc:
        logger.error(
            'Papi validation error for tenant_id=%s: %s', tenant.id, exc
        )
        raise CommandePapiError(str(exc)) from exc
    except PapiUnavailableError as exc:
        logger.error(
            'Papi unavailable for tenant_id=%s: %s', tenant.id, exc
        )
        raise CommandePapiError(
            "Service de paiement momentanément indisponible, veuillez réessayer."
        ) from exc
    except PapiError as exc:
        logger.error(
            'Papi error for tenant_id=%s: %s', tenant.id, exc
        )
        raise CommandePapiError(str(exc)) from exc

    external_reference = papi_data.get('paymentReference', reference)
    notification_token = papi_data.get('notificationToken', '')

    existing = Paiement.query.filter_by(
        commande_client_id=commande.id,
        external_reference=external_reference,
        is_active=True,
    ).first()
    if existing:
        return {
            'payment_link': existing.external_payment_id,
            'payment': existing.to_dict(),
            'commande': commande.to_dict(),
        }

    payment_method_db = PROVIDER_METHOD_MAP.get(
        method_normalized, method_normalized
    )

    paiement = Paiement(
        tenant_id=tenant.id,
        commande_client_id=commande.id,
        montant=commande.total_ttc,
        devise=commande.pays_livraison and 'MGA' or 'MGA',
        statut=StatutPaiement.EN_ATTENTE,
        type=TypePaiement.COMMANDE,
        provider='papi',
        payment_method=payment_method_db,
        external_payment_id=papi_data.get('paymentLink', ''),
        external_reference=external_reference,
        reference=external_reference,
        notes=(
            f"Paiement commande vitrine {commande.reference} "
            f"via Papi (marchand {tenant.nom})"
        ),
    )
    db.session.add(paiement)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception(
            'Echec commit Paiement commande vitrine: ref=%s', external_reference
        )
        raise

    logger.info(
        'Commande Papi payment created: paiement_id=%s ref=%s tenant_id=%s',
        paiement.id,
        external_reference,
        tenant.id,
    )

    return {
        'payment_link': papi_data.get('paymentLink', ''),
        'payment': paiement.to_dict(),
        'commande': commande.to_dict(),
    }