# web/backend/app/services/central_subscription.py
# Abonnement vu depuis le serveur central (backend embarque).
#
# Le registre de replication V1 ne couvre que produits/clients : la table
# `abonnements` locale n'est jamais alimentee par le central. Sans ce pont,
# le desk affiche « non abonne » alors que le tenant est abonne sur le web :
# la ligne locale ne contient qu'une demande creee depuis le poste (statut
# EN_ATTENTE), que l'endpoint local priorise.
#
# Deux usages :
#  - miroir au login (cf. app/services/local_auth.py) pour que le poste
#    demarre deja avec la bonne information, y compris hors-ligne ;
#  - proxy dans /abonnements/mon-abonnement (cf. app/api/v1/abonnements.py),
#    avec repli sur la copie locale des que le central est injoignable.
import logging
from datetime import datetime, timedelta

import requests

from app import db
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.tenant import StatutTenant
from app.services.replication import (
    auth_headers,
    refresh_service_token,
    remote_base_url,
)

logger = logging.getLogger(__name__)

# Delai volontairement court : l'UI attend cette reponse au chargement du
# tableau de bord. Un depot froid du central ne doit pas figer l'ecran.
_SUBSCRIPTION_TIMEOUT = 5

# Limites de plan recopies depuis le central.
_LIMIT_FIELDS = (
    'max_utilisateurs', 'max_produits', 'max_clients', 'max_admins',
    'max_employees', 'max_interns', 'max_tenants',
)


def fetch_central_subscription():
    """Reponse du central sur /abonnements/mon-abonnement, sinon None.

    None signifie « central injoignable / reponse illisible » : l'appelant
    se replie alors sur sa copie locale (mode hors-ligne).
    """
    base = remote_base_url()
    if not base:
        return None
    url = f'{base}/api/v1/abonnements/mon-abonnement'
    for attempt in (1, 2):
        try:
            response = requests.get(
                url, headers=auth_headers(), timeout=_SUBSCRIPTION_TIMEOUT,
            )
        except Exception as exc:
            logger.warning('Abonnement central injoignable : %s', exc)
            return None
        if response.status_code in (401, 403) and attempt == 1:
            if refresh_service_token():
                continue
        if response.status_code != 200:
            logger.warning(
                'Le central a repondu %s sur /abonnements/mon-abonnement',
                response.status_code,
            )
            return None
        try:
            body = response.json() or {}
        except Exception:
            logger.warning('Reponse abonnement illisible du central.')
            return None
        return body if isinstance(body, dict) else None
    return None


def _parse_dt(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _parse_statut(value):
    """Statut central ('actif' ou 'ACTIF') vers l'enum local."""
    if not value:
        return None
    raw = str(value).lower()
    for statut in StatutAbonnement:
        if statut.value == raw or statut.name.lower() == raw:
            return statut
    return None


def mirror_abonnement(tenant, payload):
    """Recopie l'abonnement central en local. Retourne la ligne (ou None).

    Les lignes locales concurrentes sont desactivees (une demande restee en
    attente sur ce poste, un ancien abonnement) : la reponse du central fait
    foi, sinon l'endpoint local continuerait de prioriser la copie perimee.
    """
    if tenant is None or not isinstance(payload, dict):
        return None
    central = payload.get('abonnement')
    if not isinstance(central, dict) or not central:
        return None

    # L'identifiant de tenant du payload est celui du central : seule la
    # reference locale (tenant.id) tient dans cette base.
    date_debut = _parse_dt(central.get('date_debut')) or datetime.utcnow()
    date_fin = _parse_dt(central.get('date_fin')) or date_debut + timedelta(days=31)

    row = Abonnement.query.filter_by(
        tenant_id=tenant.id, date_debut=date_debut,
    ).first()
    if row is None:
        row = Abonnement(tenant_id=tenant.id, date_debut=date_debut)
        db.session.add(row)

    row.date_debut = date_debut
    row.date_fin = date_fin
    statut = _parse_statut(central.get('statut'))
    if statut:
        row.statut = statut
    row.plan = central.get('plan') or row.plan
    row.montant = central.get('montant') or 0
    row.devise = central.get('devise') or row.devise or 'MGA'
    row.methode_paiement = central.get('methode_paiement')
    row.reference_paiement = central.get('reference_paiement')
    row.notes = central.get('notes')
    row.is_active = bool(central.get('is_active', True))
    for field in _LIMIT_FIELDS:
        if field in central:
            setattr(row, field, central.get(field))
    modules = central.get('modules')
    if isinstance(modules, (list, tuple)):
        row.modules = ','.join(str(m) for m in modules)
    elif isinstance(modules, str):
        row.modules = modules
    db.session.flush()

    autres = Abonnement.query.filter(
        Abonnement.tenant_id == tenant.id,
        Abonnement.id != row.id,
        Abonnement.is_active == True,
    ).all()
    for autre in autres:
        autre.is_active = False
        if autre.statut == StatutAbonnement.EN_ATTENTE:
            autre.statut = StatutAbonnement.ANNULE

    centre_tenant = payload.get('tenant') or {}
    if centre_tenant.get('plan'):
        tenant.plan = centre_tenant['plan']
    if centre_tenant.get('statut'):
        try:
            tenant.statut = StatutTenant(str(centre_tenant['statut']).lower())
        except ValueError:
            pass
    db.session.flush()
    return row
