"""Analyses métier narratives pour l'IA (ai_analytics).

Transforme les données brutes des outils en analyses compréhensables,
avec explications, détection de tendances et suggestions d'actions.
Chaque fonction respecte les permissions via ai_permissions.
"""

import logging
from typing import Optional

from app.ai import ai_tools
from app.ai.ai_permissions import (
    AIPermissionError, can_access_domain, require_domain_access,
)

logger = logging.getLogger(__name__)


def _safe(tool_fn, domain, tenant_id=None, **kwargs):
    """Exécute un outil après vérification de permission ; jamais d'erreur 500."""
    try:
        require_domain_access(domain)
    except AIPermissionError as e:
        return {'error': True, 'message': str(e), 'data_sufficient': False}
    try:
        return tool_fn(tenant_id=tenant_id, **kwargs)
    except Exception as e:
        logger.exception("Erreur outil IA %s: %s", tool_fn.__name__, e)
        return {'error': True, 'message': "Erreur lors de l'analyse.", 'data_sufficient': False}


def analyze_stock(tenant_id=None):
    """Analyse complète du stock : santé, ruptures, rotation, recommandations."""
    health = _safe(ai_tools.get_stock_health, 'stocks', tenant_id)
    low = _safe(ai_tools.get_low_stock_products, 'stocks', tenant_id, limit=10)
    turnover = _safe(ai_tools.get_stock_turnover, 'stocks', tenant_id, limit=10)

    if health.get('error') or low.get('error'):
        return {'domain': 'stocks', 'data_sufficient': False,
                'message': health.get('message') or low.get('message')}

    problems = []
    if health.get('ruptures', 0) > 0:
        problems.append(f"{health['ruptures']} produit(s) en rupture de stock.")
    if health.get('alertes', 0) > 0:
        problems.append(f"{health['alertes']} produit(s) sous le seuil d'alerte.")
    if health.get('surstock', 0) > 0:
        problems.append(f"{health['surstock']} produit(s) en surstock.")

    recommendations = []
    if low.get('items'):
        noms = ', '.join(i['nom'] for i in low['items'][:5])
        recommendations.append(f"À commander en priorité : {noms}.")
    faible_rot = turnover.get('faible_rotation', [])
    if faible_rot:
        noms = ', '.join(i['nom'] for i in faible_rot[:3])
        recommendations.append(f"Produits à faible rotation (risque de dormance) : {noms}.")

    return {
        'domain': 'stocks', 'data_sufficient': health.get('data_sufficient', False),
        'resume': health, 'alertes_stock': low.get('items', []),
        'rotation': {'forte': turnover.get('forte_rotation', []),
                     'faible': turnover.get('faible_rotation', [])},
        'problemes': problems, 'recommandations': recommendations,
    }


# === ANALYTICS_PART2 ===


def analyze_sales(tenant_id=None, days=30):
    """Analyse des ventes : CA, évolution, top produits, tendances."""
    summary = _safe(ai_tools.get_sales_summary, 'ventes', tenant_id, days=days)
    top = _safe(ai_tools.get_top_products, 'ventes', tenant_id, days=days, limit=10)
    evolution = _safe(ai_tools.get_sales_evolution, 'ventes', tenant_id, periods=8)

    if summary.get('error') or top.get('error'):
        return {'domain': 'ventes', 'data_sufficient': False,
                'message': summary.get('message') or top.get('message')}

    observations = []
    if summary.get('variation_pct') is not None:
        if summary['variation_pct'] > 0:
            observations.append(
                f"Les ventes ont augmenté de {summary['variation_pct']} % "
                f"par rapport à la période précédente.")
        elif summary['variation_pct'] < 0:
            observations.append(
                f"Les ventes ont diminué de {abs(summary['variation_pct'])} % "
                f"par rapport à la période précédente.")
        else:
            observations.append("Les ventes sont stables par rapport à la période précédente.")

    if top.get('items'):
        best = top['items'][0]
        observations.append(
            f"Produit le plus vendu : {best['nom']} "
            f"({best['quantite_vendue']} unités, {best.get('part_ca_pct', '')}% du CA).")

    trend = 'stable'
    evo_items = evolution.get('evolution', [])
    if len(evo_items) >= 2:
        last_changes = [e.get('variation_pct') for e in evo_items[-3:]
                        if e.get('variation_pct') is not None]
        if last_changes and sum(last_changes) / len(last_changes) > 10:
            trend = 'hausse'
        elif last_changes and sum(last_changes) / len(last_changes) < -10:
            trend = 'baisse'

    return {
        'domain': 'ventes', 'data_sufficient': summary.get('data_sufficient', False),
        'resume': summary, 'top_produits': top.get('items', []),
        'evolution': evo_items, 'tendance': trend, 'observations': observations,
    }


def analyze_finances(tenant_id=None, days=30):
    """Analyse financière : créances, factures en attente."""
    debts = _safe(ai_tools.get_customer_debts, 'finances', tenant_id, limit=50)
    pending = _safe(ai_tools.get_pending_invoices, 'finances', tenant_id, limit=50)

    if debts.get('error') or pending.get('error'):
        return {'domain': 'finances', 'data_sufficient': False,
                'message': debts.get('message') or pending.get('message')}

    observations = []
    total_creances = debts.get('total_creances', 0)
    nb_creances = debts.get('count', 0)
    if nb_creances > 0:
        observations.append(
            f"Vous avez {nb_creances} créance(s) pour un total de "
            f"{total_creances:,.2f} MGA.")
    else:
        observations.append("Aucune créance en cours.")

    total_attente = pending.get('total_attente', 0)
    anciens = [i for i in pending.get('items', []) if i.get('anciennete_jours', 0) > 30]
    if anciens:
        observations.append(
            f"{len(anciens)} facture(s) en attente depuis plus de 30 jours "
            f"(total {total_attente:,.2f} MGA).")

    return {
        'domain': 'finances', 'data_sufficient': True,
        'resume': {'total_creances': total_creances, 'nb_creances': nb_creances,
                   'total_factures_attente': total_attente,
                   'nb_factures_attente': pending.get('count', 0)},
        'creances': debts.get('items', []), 'factures_attente': pending.get('items', []),
        'observations': observations,
    }


def analyze_purchases(tenant_id=None, days=180):
    """Analyse des achats : fournisseurs, prix, commandes en cours."""
    suppliers = _safe(ai_tools.get_suppliers_summary, 'achats', tenant_id, days=days)
    prices = _safe(ai_tools.get_supplier_price_changes, 'achats', tenant_id, days=days)
    pending = _safe(ai_tools.get_pending_purchase_orders, 'achats', tenant_id)

    if suppliers.get('error'):
        return {'domain': 'achats', 'data_sufficient': False,
                'message': suppliers.get('message')}

    observations = []
    hausses = [c for c in prices.get('items', []) if c.get('evolution_pct', 0) > 0]
    if hausses:
        top = hausses[0]
        observations.append(
            f"Le prix d'achat de {top['produit_nom']} chez "
            f"{top['fournisseur_nom']} a augmenté de {top['evolution_pct']} %.")
    nb_pending = pending.get('count', 0)
    if nb_pending:
        observations.append(f"{nb_pending} commande(s) fournisseur(s) en cours.")

    return {
        'domain': 'achats', 'data_sufficient': suppliers.get('data_sufficient', False),
        'resume': suppliers,
        'fournisseurs': suppliers.get('top_fournisseurs', []),
        'variations_prix': prices.get('items', []),
        'commandes_en_cours': pending.get('items', []),
        'observations': observations,
    }


def analyze_clients(tenant_id=None, days=90):
    """Analyse de la clientèle."""
    data = _safe(ai_tools.get_clients_summary, 'clients', tenant_id, days=days)
    if data.get('error'):
        return {'domain': 'clients', 'data_sufficient': False, 'message': data.get('message')}
    observations = []
    if data.get('nb_clients') is not None:
        observations.append(f"Vous avez {data['nb_clients']} client(s) actif(s).")
    if data.get('top_clients'):
        best = data['top_clients'][0]
        observations.append(f"Meilleur client : {best['nom']} ({best['ca_ttc']:,.2f} MGA).")
    return {
        'domain': 'clients', 'data_sufficient': data.get('data_sufficient', False),
        'resume': data, 'top_clients': data.get('top_clients', []),
        'observations': observations,
    }
