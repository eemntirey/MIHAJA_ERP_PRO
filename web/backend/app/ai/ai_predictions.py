"""Prédictions pour l'IA (ai_predictions).

Prévisions basées sur les données historiques réelles :
- risque de rupture par produit (avec probabilité / jours restants) ;
- tendance des ventes (croissance/décroissance, score de confiance) ;
- prévision de demande par produit.

Quand les données sont insuffisantes, le module le déclare explicitement
plutôt que de produire une estimation non fiable.
"""

import logging
import numpy as np
from datetime import datetime, timedelta

from sqlalchemy import func
from app import db
from app.models.produit import Produit
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.security.tenant import get_current_tenant_id

logger = logging.getLogger(__name__)

SALES_STATUTS_VALIDES = ('payee', 'en_attente')
MIN_POINTS = 4


def _resolve_tenant(tenant_id=None):
    return get_current_tenant_id() or tenant_id


def _rupture_item(p, stock, avg, prob, prio, confidence, explanation):
    days = float(stock) / avg if avg > 0 else 0.0
    return {
        'produit_id': p.id, 'nom': p.nom, 'reference': p.reference,
        'stock_actuel': round(stock, 2), 'seuil_alerte': float(p.seuil_alerte or 0),
        'consommation_moyenne_jour': round(avg, 2),
        'jours_restants': round(days, 1),
        'probabilite_rupture_pct': prob, 'priorite': prio,
        'confidence_score': confidence, 'explanation': explanation,
    }


def predict_stock_rupture(tenant_id=None, horizon_days=14):
    """Prédit le risque de rupture par produit dans les N jours."""
    tid = _resolve_tenant(tenant_id)
    if tid is None:
        return {'items': [], 'count': 0, 'data_sufficient': False,
                'message': "Aucun tenant actif."}

    produits = Produit.query.filter(
        Produit.is_active == True, Produit.tenant_id == tid).all()

    predictions = []
    for p in produits:
        stock = float(p.quantite_stock or 0)
        if stock <= 0:
            predictions.append(_rupture_item(
                p, stock, 0.0, 100.0, 'CRITIQUE', 1.0, "Produit déjà en rupture."))
            continue

        start = datetime.utcnow() - timedelta(days=90)
        rows = db.session.query(
            Vente.date, func.sum(LigneVente.quantite)
        ).join(Vente, LigneVente.vente_id == Vente.id).filter(
            LigneVente.is_active == True, LigneVente.tenant_id == tid,
            LigneVente.produit_id == p.id,
            Vente.is_active == True, Vente.tenant_id == tid,
            Vente.statut.in_(SALES_STATUTS_VALIDES), Vente.date >= start,
        ).group_by(Vente.date).all()

        daily_qty = [float(q or 0) for _, q in rows]
        n_points = len(daily_qty)
        if n_points < 2:
            continue

        avg = float(np.mean(daily_qty))
        if avg <= 0:
            continue
        days_remaining = stock / avg
        std = float(np.std(daily_qty))
        cv = std / avg if avg > 0 else 0.0
        confidence = min(0.95, max(0.3, (n_points / 20.0) * (1.0 - min(cv, 1.0) * 0.5)))

        if days_remaining <= horizon_days:
            prob = min(100.0, max(50.0, (1.0 - days_remaining / horizon_days) * 100.0))
            prio = 'CRITIQUE' if days_remaining <= 3 else ('HAUTE' if days_remaining <= 7 else 'MOYENNE')
            predictions.append(_rupture_item(
                p, stock, avg, round(prob, 1), prio, round(confidence, 2),
                f"Consommation moyenne {avg:.2f}/jour. "
                f"Stock estimé suffisant {days_remaining:.1f} jour(s)."))

    predictions.sort(key=lambda x: x.get('jours_restants', 999))
    return {'tenant_id': tid, 'horizon_days': horizon_days, 'items': predictions,
            'count': len(predictions), 'data_sufficient': len(predictions) > 0}


# === PREDICTIONS_PART2 ===


def _trend_explanation(trend, rel_slope, confidence):
    if trend in ('forte_croissance', 'croissante'):
        return (f"Tendance à la hausse détectée ({rel_slope:+.2f} %/semaine). "
                f"Confiance : {confidence:.0%}.")
    if trend in ('forte_decroissance', 'decroissante'):
        return (f"Tendance à la baisse détectée ({rel_slope:+.2f} %/semaine). "
                f"Confiance : {confidence:.0%}.")
    return (f"Tendance stable (variation {rel_slope:+.2f} %/semaine). "
            f"Confiance : {confidence:.0%}.")


def predict_sales_trend(tenant_id=None, weeks=12):
    """Tendance des ventes globales (régression linéaire sur CA hebdo)."""
    tid = _resolve_tenant(tenant_id)
    if tid is None:
        return {'trend': 'indetermine', 'data_sufficient': False,
                'message': "Aucun tenant actif."}

    start = datetime.utcnow() - timedelta(weeks=weeks)
    rows = db.session.query(
        Vente.date, func.coalesce(func.sum(Vente.total_ttc), 0)
    ).filter(
        Vente.is_active == True, Vente.tenant_id == tid,
        Vente.statut.in_(SALES_STATUTS_VALIDES), Vente.date >= start,
    ).group_by(Vente.date).all()

    weekly = {}
    for d, total in rows:
        if not d:
            continue
        key = d.strftime('%G-W%V')
        weekly[key] = weekly.get(key, 0.0) + float(total or 0)

    items = [v for _, v in sorted(weekly.items())]
    n = len(items)

    if n < MIN_POINTS:
        return {
            'trend': 'indetermine', 'data_sufficient': False,
            'nb_semaines': n, 'minimum_requis': MIN_POINTS,
            'message': "Données insuffisantes pour produire une prévision fiable.",
            'serie': [{'periode': k, 'total_ttc': round(v, 2)}
                      for k, v in sorted(weekly.items())],
        }

    y = np.array(items, dtype=float)
    x = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    mean_val = float(np.mean(y))
    rel_slope = (slope / mean_val * 100) if mean_val > 0 else 0.0

    if rel_slope > 3:
        trend = 'forte_croissance'
    elif rel_slope > 0.5:
        trend = 'croissante'
    elif rel_slope < -3:
        trend = 'forte_decroissance'
    elif rel_slope < -0.5:
        trend = 'decroissante'
    else:
        trend = 'stable'

    confidence = min(0.95, max(0.3, r_squared * (n / (n + MIN_POINTS))))

    return {
        'tenant_id': tid, 'trend': trend, 'data_sufficient': True,
        'nb_semaines': n, 'ca_moyen_hebdo': round(mean_val, 2),
        'pente_relative_pct': round(rel_slope, 2),
        'confidence_score': round(confidence, 2), 'r_squared': round(r_squared, 3),
        'serie': [{'periode': k, 'total_ttc': round(v, 2)}
                  for k, v in sorted(weekly.items())],
        'explication': _trend_explanation(trend, rel_slope, confidence),
    }


def predict_demand(tenant_id=None, produit_id=None, weeks_ahead=4):
    """Prévision de demande hebdomadaire pour un produit (régression linéaire)."""
    tid = _resolve_tenant(tenant_id)
    if tid is None or produit_id is None:
        return {'data_sufficient': False, 'message': "Paramètres manquants."}

    produit = db.session.query(Produit).filter(
        Produit.id == int(produit_id), Produit.tenant_id == tid,
        Produit.is_active == True).first()
    if not produit:
        return {'data_sufficient': False, 'message': "Produit introuvable."}

    start = datetime.utcnow() - timedelta(weeks=12)
    rows = db.session.query(
        Vente.date, func.sum(LigneVente.quantite)
    ).join(Vente, LigneVente.vente_id == Vente.id).filter(
        LigneVente.is_active == True, LigneVente.tenant_id == tid,
        LigneVente.produit_id == int(produit_id),
        Vente.is_active == True, Vente.tenant_id == tid,
        Vente.statut.in_(SALES_STATUTS_VALIDES), Vente.date >= start,
    ).group_by(Vente.date).all()

    weekly = {}
    for d, q in rows:
        if not d:
            continue
        key = d.strftime('%G-W%V')
        weekly[key] = weekly.get(key, 0.0) + float(q or 0)

    items = [v for _, v in sorted(weekly.items())]
    n = len(items)

    if n < MIN_POINTS:
        return {
            'produit_id': int(produit_id), 'produit_nom': produit.nom,
            'data_sufficient': False, 'nb_semaines': n, 'minimum_requis': MIN_POINTS,
            'message': "Données insuffisantes pour une prévision fiable.",
            'historique': [{'periode': k, 'quantite': round(v, 2)}
                           for k, v in sorted(weekly.items())],
        }

    y = np.array(items, dtype=float)
    x = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)

    forecasts = []
    for i in range(1, weeks_ahead + 1):
        val = max(0.0, float(slope * (n - 1 + i) + intercept))
        forecasts.append({'semaine': i, 'quantite_previste': round(val, 2)})

    y_pred = slope * x + intercept
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    confidence = min(0.92, max(0.3, r_squared * (n / (n + MIN_POINTS))))

    return {
        'produit_id': int(produit_id), 'produit_nom': produit.nom,
        'data_sufficient': True,
        'tendance': 'hausse' if slope > 0.05 else ('baisse' if slope < -0.05 else 'stable'),
        'previsions': forecasts,
        'moyenne_historique': round(float(np.mean(y)), 2),
        'confidence_score': round(confidence, 2), 'r_squared': round(r_squared, 3),
        'explication': (
            f"La demande hebdomadaire est estimée à {np.mean(y):.2f} unités en moyenne. "
            f"Prévision sur {weeks_ahead} semaine(s), confiance {confidence:.0%}."),
    }
