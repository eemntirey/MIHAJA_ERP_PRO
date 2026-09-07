"""Tenant-level Papi merchant configuration.

Ce service encapsule :
- le chiffrement / déchiffrement des clés API Papi du tenant (Fernet) ;
- la construction d'un PapiClient configuré avec les clés du tenant ;
- la mise à jour / lecture du statut Papi / vitrine d'un tenant.

Les clés secrètes ne sont jamais renvoyées au frontend : seul un booléen
``papi_configured`` et un timestamp sont exposés.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app import db
from app.config.settings import Config
from app.models.tenant import Tenant, StatutTenant
from app.security.encryption import decrypt_text, encrypt_text
from app.services.papi.client import PapiClient
from app.services.papi.errors import PapiError

logger = logging.getLogger(__name__)


VALID_ENVIRONMENTS = ('sandbox', 'production')


class TenantPapiConfigError(ValueError):
    """Erreur de configuration Papi côté tenant (clé invalide, etc.)."""


def _normalize_environment(value: Optional[str]) -> str:
    env = (value or '').strip().lower() or Config.PAPI_ENVIRONMENT or 'sandbox'
    if env not in VALID_ENVIRONMENTS:
        raise TenantPapiConfigError(
            f"Environnement Papi invalide: {value}. Attendu: {', '.join(VALID_ENVIRONMENTS)}"
        )
    return env


def get_papi_client_for_tenant(tenant: Tenant) -> Optional[PapiClient]:
    """Construit un PapiClient configuré avec la clé du tenant.

    Retourne ``None`` si le tenant n'a pas configuré son compte Papi.
    Lève ``TenantPapiConfigError`` si la clé stockée est corrompue
    (impossible de déchiffrer).
    """
    if not tenant or not tenant.papi_api_key_encrypted:
        return None
    try:
        api_key = decrypt_text(tenant.papi_api_key_encrypted)
    except Exception as exc:
        logger.error(
            'Papi api key corrompue pour tenant_id=%s: %s', tenant.id, exc
        )
        raise TenantPapiConfigError(
            "Impossible de déchiffrer la clé Papi du tenant. "
            "Veuillez reconfigurer le paiement."
        ) from exc

    return PapiClient(
        api_url=Config.PAPI_API_URL,
        api_key=api_key,
        environment=_normalize_environment(tenant.papi_environment),
    )


def get_webhook_secret_for_tenant(tenant: Optional[Tenant]) -> Optional[str]:
    """Retourne le secret webhook Papi du tenant, ou None."""
    if not tenant or not tenant.papi_webhook_secret_encrypted:
        return None
    try:
        return decrypt_text(tenant.papi_webhook_secret_encrypted)
    except Exception as exc:
        logger.error(
            'Papi webhook secret corrompu pour tenant_id=%s: %s', tenant.id, exc
        )
        return None


def update_tenant_papi_settings(
    tenant: Tenant,
    papi_api_key: Optional[str] = None,
    papi_webhook_secret: Optional[str] = None,
    papi_environment: Optional[str] = None,
    clear: bool = False,
) -> Tenant:
    """Met à jour la configuration Papi du tenant.

    - ``clear=True`` supprime toutes les clés Papi stockées et force
      ``vitrine_enabled=False`` (le tenant ne peut plus recevoir de
      paiement en ligne).
    - Sinon, chaque champ fourni est mis à jour et chiffré.
    Les champs ``None`` ne sont pas modifiés.
    """
    if clear:
        tenant.papi_api_key_encrypted = None
        tenant.papi_webhook_secret_encrypted = None
        tenant.papi_environment = None
        tenant.papi_configured_at = None
        tenant.vitrine_enabled = False
        tenant.vitrine_enabled_at = None
        db.session.add(tenant)
        db.session.commit()
        logger.info('Papi settings cleared for tenant_id=%s', tenant.id)
        return tenant

    changed = False
    if papi_api_key is not None and papi_api_key.strip():
        tenant.papi_api_key_encrypted = encrypt_text(papi_api_key.strip())
        tenant.papi_configured_at = datetime.utcnow()
        changed = True

    if papi_webhook_secret is not None and papi_webhook_secret.strip():
        tenant.papi_webhook_secret_encrypted = encrypt_text(
            papi_webhook_secret.strip()
        )

    if papi_environment is not None:
        tenant.papi_environment = _normalize_environment(papi_environment)
        changed = True

    if changed and not tenant.has_papi_configured():
        pass

    db.session.add(tenant)
    db.session.commit()
    logger.info(
        'Papi settings updated for tenant_id=%s (changed=%s)',
        tenant.id,
        changed,
    )
    return tenant


def set_vitrine_enabled(tenant: Tenant, enabled: bool) -> Tenant:
    """Active ou désactive la vitrine publique du tenant.

    Pour activer la vitrine, le tenant DOIT avoir configuré son compte
    Papi marchand (clé API présente). Sinon une erreur est levée.
    """
    enabled = bool(enabled)
    if enabled and not tenant.has_papi_configured():
        raise TenantPapiConfigError(
            "Impossible d'activer la vitrine : configurez d'abord votre "
            "compte marchand Papi dans les paramètres de paiement."
        )

    tenant.vitrine_enabled = enabled
    tenant.vitrine_enabled_at = datetime.utcnow() if enabled else None

    statut = (
        tenant.statut.value if hasattr(tenant.statut, 'value') else tenant.statut
    )
    if enabled and statut in (StatutTenant.INACTIF.value, StatutTenant.BLOQUE.value):
        raise TenantPapiConfigError(
            "Impossible d'activer la vitrine : votre compte est suspendu."
        )

    db.session.add(tenant)
    db.session.commit()
    logger.info(
        'Vitrine %s for tenant_id=%s',
        'enabled' if enabled else 'disabled',
        tenant.id,
    )
    return tenant


def test_tenant_papi_credentials(tenant: Tenant) -> dict:
    """Vérifie que la clé Papi du tenant est valide (appel léger à l'API).

    On déclenche un appel avec un payload invalide exprès : une clé
    correcte doit répondre avec une erreur 400 (validation), une clé
    incorrecte avec 401/403 (auth). Cela permet de distinguer auth vs
    validation sans dépendre d'un endpoint de health officiel.
    """
    client = get_papi_client_for_tenant(tenant)
    if not client:
        raise TenantPapiConfigError("Aucune clé Papi configurée pour ce tenant.")

    try:
        client.create_payment_link(
            {
                'amount': 1,
                'clientName': 'MIHAJA-ERP-PRO connectivity check',
                'reference': f"TEST-{tenant.id}-{datetime.utcnow().timestamp()}",
                'description': 'Connectivity test',
                'successUrl': 'https://example.com/success',
                'failureUrl': 'https://example.com/failure',
                'notificationUrl': 'https://example.com/webhook',
                'validDuration': 1,
                'provider': 'MVOLA',
            }
        )
        return {'ok': True}
    except PapiError as exc:
        message = str(exc).lower()
        if 'invalide' in message or 'auth' in message:
            raise TenantPapiConfigError(
                "Clé Papi refusée par le serveur. Vérifiez votre clé."
            ) from exc
        return {'ok': True, 'note': str(exc)}