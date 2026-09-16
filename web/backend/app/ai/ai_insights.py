"""Insights proactifs pour l'IA (ai_insights).

Détecte automatiquement les points d'attention et opportunités de l'entreprise
à partir des données réelles, avec 4 niveaux de sévérité :

  🔴 critique  - action immédiate requise
  🟠 attention - situation à traiter rapidement
  🟡 surveillance - à surveiller
  🟢 opportunité / positif

Chaque insight contient : problème, données concernées, explication,
impact potentiel, et recommandation. Aucune accusation d'utilisateur.
"""

import logging
from typing import List, Optional

from app.ai import ai_tools
from app.ai.ai_analytics import analyze_stock, analyze_sales, analyze_finances, analyze_purchases
from app.ai.ai_permissions import AIPermissionError, can_access_domain, require_domain_access
from app.ai.anomalies import detect_stock_anomalies, detect_sales_anomalies, detect_payment_anomalies
from app.ai.recommendations import suggest_reorders

logger = logging.getLogger(__name__)

CRITIQUE = 'critique'
ATTENTION = 'attention'
SURVEILLANCE = 'surveillance'
OPPORTUNITE = 'opportunite'


def _push(insights: List[dict], severity: str, code: str, title: str,
          detail: str, data=None, explanation: str = '',
          impact: str = '', recommendation: str = '',
          actions: Optional[List[dict]] = None):
    insights.append({
        'severity': severity,
        'icon': {'critique': '🔴', 'attention': '🟠', 'surveillance': '🟡', 'opportunite': '🟢'}[severity],
        'code': code, 'title': title, 'detail': detail,
        'data': data or [], 'explanation': explanation,
        'impact': impact, 'recommendation': recommendation,
        'actions': actions or [],
    })


def _defer(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except AIPermissionError:
        return None
    except Exception as e:
        logger.exception("Erreur insight: %s", e)
        return None


def generate_insights(tenant_id=None) -> List[dict]:
    """Génère la liste des insights pour le tenant actif."""
    insights: List[dict] = []

    _insights_stock(insights, tenant_id)
    _insights_sales(insights, tenant_id)
    _insights_finances(insights, tenant_id)
    _insights_purchases(insights, tenant_id)
    _insights_anomalies(insights, tenant_id)

    order = {CRITIQUE: 0, ATTENTION: 1, SURVEILLANCE: 2, OPPORTUNITE: 3}
    insights.sort(key=lambda x: order.get(x['severity'], 9))
    return insights


def _insights_stock(insights, tenant_id):
    if not can_access_domain('stocks'):
        return
    health = _defer(analyze_stock, tenant_id)
    if not health or health.get('error'):
        return

    data = health.get('resume', {})
    ruptures = data.get('ruptures', 0)
    alertes = data.get('alertes', 0)

    if ruptures > 0:
        noms = ', '.join(a['nom'] for a in health.get('alertes_stock', [])[:5])
        _push(insights, CRITIQUE, 'RUPTURE_STOCK',
              f"rupture de stock détectée : {ruptures} produit(s)",
              f"Le stock de {ruptures} produit(s) est à zéro. {noms}.",
              data=health.get('alertes_stock', [])[:10],
              explanation="Le stock actuel est <= 0. Aucune vente supplémentaire n'est possible.",
              impact="Perte de chiffre d'affaires et risque de déception client.",
              recommendation="Passer une commande fournisseur immédiate pour ces produits.",
              actions=[{'type': 'view_alertes_stock', 'label': 'Voir les alertes stock'},
                       {'type': 'prepare_purchase_order', 'label': 'Préparer une commande fournisseur'}])

    elif alertes > 0:
        noms = ', '.join(a['nom'] for a in health.get('alertes_stock', [])[:5])
        _push(insights, ATTENTION, 'STOCK_ALERTE',
              f"produit(s) sous le seuil d'alerte : {alertes}",
              f"{alertes} produit(s) ont un stock inférieur ou égal au seuil d'alerte. {noms}.",
              data=health.get('alertes_stock', [])[:10],
              explanation="Le stock actuel est au niveau ou en dessous du seuil d'alerte défini.",
              impact="Rupture probable dans les prochains jours si aucune action.",
              recommendation="Planifier un réapprovisionnement.",
              actions=[{'type': 'prepare_purchase_order', 'label': 'Préparer une commande'}])

    # Forte rotation (opportunité)
    forte = health.get('rotation', {}).get('forte', [])
    if forte:
        _push(insights, OPPORTUNITE, 'FORTE_ROTATION',
              "produit(s) à forte rotation identifié(s)",
              f"{len(forte)} produit(s) se vendent très rapidement.",
              data=forte[:5],
              explanation="La vitesse de vente élevée indique une demande forte.",
              impact="Opportunité de marge si le réapprovisionnement suit la demande.",
              recommendation="S'assurer d'un stock de sécurité suffisant pour éviter les ruptures.",
              actions=[{'type': 'prepare_purchase_order', 'label': 'Réapprovisionner'}])


def _insights_sales(insights, tenant_id):
    if not can_access_domain('ventes'):
        return
    sales = _defer(analyze_sales, tenant_id, days=30)
    if not sales or sales.get('error'):
        return
    resume = sales.get('resume', {})
    variation = resume.get('variation_pct')

    if variation is not None and variation < -15:
        _push(insights, ATTENTION, 'BAISSE_VENTES',
              f"baisse des ventes de {abs(variation)} %",
              f"Le chiffre d'affaires a chuté de {abs(variation)} % par rapport à la période précédente.",
              data=resume,
              explanation="Le CA de la période est nettement inférieur à la période précédente.",
              impact="Baisse de rentabilité si la tendance se confirme.",
              recommendation="Analyser les produits en baisse et vérifier l'activité commerciale.",
              actions=[{'type': 'view_sales', 'label': 'Voir les ventes'}])
    elif variation is not None and variation > 15:
        _push(insights, OPPORTUNITE, 'HAUSSE_VENTES',
              f"hausse des ventes de {variation} %",
              f"Le chiffre d'affaires a augmenté de {variation} % par rapport à la période précédente.",
              data=resume,
              explanation="Le CA de la période dépasse nettement la période précédente.",
              impact="Opportunité de renforcer les stocks pour accompagner la demande.",
              recommendation="Vérifier que le stock suit la hausse de la demande.",
              actions=[{'type': 'view_stock', 'label': 'Voir le stock'}])


def _insights_finances(insights, tenant_id):
    if not can_access_domain('finances'):
        return
    fin = _defer(analyze_finances, tenant_id)
    if not fin or fin.get('error'):
        return
    resume = fin.get('resume', {})
    nb_creances = resume.get('nb_creances', 0)
    total_creances = resume.get('total_creances', 0)

    if nb_creances > 0:
        severity = CRITIQUE if nb_creances >= 5 else ATTENTION
        _push(insights, severity, 'CREANCES_IMPORTANTES',
              f"{nb_creances} créance(s) pour {total_creances:,.2f} MGA",
              f"Des clients doivent encore régler {nb_creances} facture(s).",
              data=fin.get('creances', [])[:10],
              explanation="Ces factures sont non payées ou payées partiellement.",
              impact="Impact sur la trésorerie de l'entreprise.",
              recommendation="Relancer les clients concernés.",
              actions=[{'type': 'view_debts', 'label': 'Voir les créances'}])

    anciens = [i for i in fin.get('factures_attente', []) if i.get('anciennete_jours', 0) > 30]
    if anciens:
        _push(insights, ATTENTION, 'FACTURES_RETARDEES',
              f"{len(anciens)} facture(s) en retard de plus de 30 jours",
              "Certaines factures en attente datent de plus d'un mois.",
              data=anciens[:10],
              explanation="L'ancienneté élevée augmente le risque d'impayé.",
              impact="Risque sur la trésorerie.",
              recommendation="Vérifier ces factures et contacter les clients.",
              actions=[{'type': 'view_pending_invoices', 'label': 'Voir les factures en attente'}])


def _insights_purchases(insights, tenant_id):
    if not can_access_domain('achats'):
        return
    achats = _defer(analyze_purchases, tenant_id, days=180)
    if not achats or achats.get('error'):
        return
    hausses = [c for c in achats.get('variations_prix', []) if c.get('evolution_pct', 0) > 10]
    if hausses:
        top = hausses[0]
        _push(insights, SURVEILLANCE, 'HAUSSE_PRIX_ACHAT',
              f"hausse détectée : {top['produit_nom']} (+{top['evolution_pct']} %)",
              f"Le prix d'achat de {top['produit_nom']} chez {top['fournisseur_nom']} a augmenté.",
              data=hausses[:5],
              explanation="Le prix moyen d'achat récent dépasse nettement le prix ancien.",
              impact="Marge de revente compressée si le prix de vente n'est pas ajusté.",
              recommendation="Vérifier si le prix de vente peut être ajusté ou chercher un autre fournisseur.",
              actions=[{'type': 'view_suppliers', 'label': 'Voir les fournisseurs'}])


def _insights_anomalies(insights, tenant_id):
    stock_anom = _defer(detect_stock_anomalies, tenant_id)
    if stock_anom and stock_anom.get('count', 0) > 0:
        high = [a for a in stock_anom.get('anomalies', []) if a.get('severity') == 'high']
        if high:
            _push(insights, SURVEILLANCE, 'ANOMALIE_STOCK',
                  f"{len(high)} mouvement(s) de stock anormal(aux)",
                  "Des quantités de mouvement de stock s'écartent fortement de la moyenne.",
                  data=high[:5],
                  explanation="L'écart (z-score) dépasse le seuil d'alerte statistique.",
                  impact="Erreur de saisie possible ou vol. À vérifier sans accusation.",
                  recommendation="Vérifier les mouvements concernés.",
                  actions=[{'type': 'view_stock', 'label': 'Voir les mouvements'}])

    pay_anom = _defer(detect_payment_anomalies, tenant_id)
    if pay_anom and pay_anom.get('count', 0) > 0:
        _push(insights, ATTENTION, 'FACTURES_RETARDEES_CRIT',
              f"{pay_anom['count']} facture(s) impayées en retard critique",
              "Certaines factures impayées datent de plus de 30 jours.",
              data=pay_anom.get('anomalies', [])[:5],
              explanation="Retard de paiement supérieur à 30 jours.",
              impact="Risque d'impayé et tension de trésorerie.",
              recommendation="Contacter les clients et vérifier les échéances.",
              actions=[{'type': 'view_debts', 'label': 'Voir les créances'}])
