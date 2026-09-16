"""Outils de lecture de données réelles pour l'IA (ai_tools).

Chaque outil :
- filtre explicitement par ``tenant_id`` (isolation multi-tenant stricte,
  cumulée avec le filtre global SQLAlchemy en contexte de requête) ;
- n'utilise que des agrégations SQL et des limites de taille ;
- n'invente jamais de données : en l'absence de données suffisantes,
  l'outil le signale via ``data_sufficient = False``.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import func

from app import db
from app.models.produit import Produit
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.models.facture import Facture
from app.models.paiement import Paiement, StatutPaiement
from app.models.commande_achat import CommandeAchat, StatutCommandeAchat
from app.models.ligne_achat import LigneAchat
from app.security.tenant import get_current_tenant_id

logger = logging.getLogger(__name__)

SALES_STATUTS_VALIDES = ('payee', 'en_attente')
PAID_STATUTS = (StatutPaiement.SUCCESS, StatutPaiement.CONFIRME)


def resolve_tenant_id(tenant_id=None):
    current = get_current_tenant_id()
    return current or tenant_id


def no_tenant_result(message="Aucune entreprise (tenant) active identifiée pour cette requête."):
    return {'tenant_id': None, 'items': [], 'data_sufficient': False, 'message': message}


# === AI_TOOLS_PART2 ===


def get_sales_summary(tenant_id=None, days=30):
    """Résumé des ventes sur les N derniers jours (CA, volume, panier moyen)."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None:
        return no_tenant_result()
    days = max(1, min(int(days or 30), 365))
    start = datetime.utcnow() - timedelta(days=days)

    nb, ca, ca_ht = db.session.query(
        func.count(Vente.id),
        func.coalesce(func.sum(Vente.total_ttc), 0),
        func.coalesce(func.sum(Vente.total_ht), 0),
    ).filter(
        Vente.is_active == True, Vente.tenant_id == tid,
        Vente.statut.in_(SALES_STATUTS_VALIDES), Vente.date >= start,
    ).one()

    prev_start = start - timedelta(days=days)
    prev_nb, prev_ca, _ = db.session.query(
        func.count(Vente.id),
        func.coalesce(func.sum(Vente.total_ttc), 0),
        func.coalesce(func.sum(Vente.total_ht), 0),
    ).filter(
        Vente.is_active == True, Vente.tenant_id == tid,
        Vente.statut.in_(SALES_STATUTS_VALIDES),
        Vente.date >= prev_start, Vente.date < start,
    ).one()

    ca = float(ca or 0); prev_ca = float(prev_ca or 0); nb = int(nb or 0)
    return {
        'tenant_id': tid, 'days': days,
        'total_ttc': round(ca, 2), 'total_ht': round(float(ca_ht or 0), 2),
        'nb_ventes': nb, 'panier_moyen': round(ca / nb, 2) if nb else 0.0,
        'periode_precedente_ttc': round(prev_ca, 2),
        'variation_pct': round(((ca - prev_ca) / prev_ca) * 100, 1) if prev_ca > 0 else None,
        'data_sufficient': nb > 0,
    }


def get_sales_evolution(tenant_id=None, granularity='week', periods=8):
    """Évolution du CA par jour / semaine / mois (série temporelle)."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None:
        return no_tenant_result()
    periods = max(2, min(int(periods or 8), 26))
    if granularity == 'day':
        step = timedelta(days=1); fmt = '%Y-%m-%d'
    elif granularity == 'month':
        step = timedelta(days=30); fmt = '%Y-%m'
    else:
        step = timedelta(days=7); fmt = '%G-W%V'
    start = datetime.utcnow() - step * periods

    rows = db.session.query(
        Vente.date, func.coalesce(func.sum(Vente.total_ttc), 0)
    ).filter(
        Vente.is_active == True, Vente.tenant_id == tid,
        Vente.statut.in_(SALES_STATUTS_VALIDES), Vente.date >= start,
    ).group_by(Vente.date).all()

    series = {}
    for d, total in rows:
        if not d:
            continue
        key = d.strftime(fmt)
        series[key] = series.get(key, 0.0) + float(total or 0)

    items = [{'periode': k, 'total_ttc': round(v, 2)} for k, v in sorted(series.items())]
    evolution = []
    for i in range(1, len(items)):
        prev = items[i - 1]['total_ttc']; cur = items[i]['total_ttc']
        change = round(((cur - prev) / prev) * 100, 1) if prev > 0 else None
        evolution.append({**items[i], 'variation_pct': change})

    return {
        'tenant_id': tid, 'granularity': granularity,
        'series': items, 'evolution': evolution,
        'data_sufficient': len(items) >= 2,
    }


# === AI_TOOLS_PART2B ===


def get_top_products(tenant_id=None, days=30, limit=10):
    """Meilleures ventes (produits) sur la période."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None:
        return no_tenant_result()
    days = max(1, min(int(days or 30), 365))
    limit = max(1, min(int(limit or 10), 50))
    start = datetime.utcnow() - timedelta(days=days)

    rows = db.session.query(
        LigneVente.produit_id, Produit.nom,
        func.sum(LigneVente.quantite).label('qte'),
        func.sum(func.coalesce(LigneVente.total_ttc, LigneVente.total_ht, 0)).label('ca'),
    ).join(Vente, LigneVente.vente_id == Vente.id).join(
        Produit, LigneVente.produit_id == Produit.id
    ).filter(
        LigneVente.is_active == True, LigneVente.tenant_id == tid,
        Vente.is_active == True, Vente.tenant_id == tid,
        Vente.statut.in_(SALES_STATUTS_VALIDES), Vente.date >= start,
    ).group_by(LigneVente.produit_id, Produit.nom).order_by(
        func.sum(LigneVente.quantite).desc()
    ).limit(limit).all()

    total_ca = sum(float(r.ca or 0) for r in rows)
    items = [{
        'produit_id': r.produit_id, 'nom': r.nom,
        'quantite_vendue': float(r.qte or 0), 'ca_ttc': round(float(r.ca or 0), 2),
        'part_ca_pct': round((float(r.ca or 0) / total_ca) * 100, 1) if total_ca > 0 else None,
    } for r in rows]
    return {'tenant_id': tid, 'days': days, 'items': items, 'count': len(items),
            'data_sufficient': len(items) > 0}


def get_product_sales_history(tenant_id=None, produit_id=None, weeks=8):
    """Historique hebdomadaire des quantités vendues d'un produit."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None or produit_id is None:
        return no_tenant_result()
    weeks = max(2, min(int(weeks or 8), 52))
    start = datetime.utcnow() - timedelta(weeks=weeks)

    produit = db.session.query(Produit).filter(
        Produit.id == int(produit_id), Produit.tenant_id == tid, Produit.is_active == True
    ).first()
    if not produit:
        return {'tenant_id': tid, 'items': [], 'data_sufficient': False,
                'message': "Produit introuvable dans cette entreprise."}

    rows = db.session.query(Vente.date, LigneVente.quantite).join(
        Vente, LigneVente.vente_id == Vente.id
    ).filter(
        LigneVente.is_active == True, LigneVente.tenant_id == tid,
        LigneVente.produit_id == int(produit_id),
        Vente.is_active == True, Vente.tenant_id == tid,
        Vente.statut.in_(SALES_STATUTS_VALIDES), Vente.date >= start,
    ).all()

    weekly = {}
    for d, q in rows:
        if not d:
            continue
        key = d.strftime('%G-W%V')
        weekly[key] = weekly.get(key, 0.0) + float(q or 0)

    items = [{'semaine': k, 'quantite': round(v, 2)} for k, v in sorted(weekly.items())]
    qtes = [i['quantite'] for i in items]
    trend = 'stable'
    if len(qtes) >= 2 and qtes[-1] != qtes[0]:
        if qtes[-1] > qtes[0] * 1.2:
            trend = 'hausse'
        elif qtes[-1] < qtes[0] * 0.8:
            trend = 'baisse'
    return {
        'tenant_id': tid, 'produit_id': int(produit_id), 'produit_nom': produit.nom,
        'items': items, 'total_quantite': round(sum(qtes), 2),
        'moyenne_hebdo': round(sum(qtes) / len(qtes), 2) if qtes else 0.0,
        'tendance': trend, 'data_sufficient': len(items) >= 2,
    }


# === AI_TOOLS_PART3 ===


def get_low_stock_products(tenant_id=None, limit=50):
    """Produits sous le seuil d'alerte ou en rupture."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None:
        return no_tenant_result()
    limit = max(1, min(int(limit or 50), 100))
    produits = Produit.query.filter(
        Produit.is_active == True, Produit.tenant_id == tid,
        Produit.quantite_stock <= Produit.seuil_alerte,
    ).order_by(Produit.quantite_stock.asc()).limit(limit).all()

    items = [{
        'produit_id': p.id, 'nom': p.nom, 'reference': p.reference,
        'stock_actuel': float(p.quantite_stock or 0),
        'seuil_alerte': float(p.seuil_alerte or 0),
        'seuil_critique': float(p.seuil_critique or 0),
        'fournisseur_id': p.fournisseur_id,
        'statut': 'rupture' if float(p.quantite_stock or 0) <= 0 else 'alerte',
    } for p in produits]
    return {'tenant_id': tid, 'items': items, 'count': len(items),
            'data_sufficient': True}


def get_stock_health(tenant_id=None):
    """Vue d'ensemble de la santé du stock (ruptures, alertes, surstock, valeur)."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None:
        return no_tenant_result()

    total = db.session.query(func.count(Produit.id)).filter(
        Produit.is_active == True, Produit.tenant_id == tid
    ).scalar() or 0
    ruptures = db.session.query(func.count(Produit.id)).filter(
        Produit.is_active == True, Produit.tenant_id == tid,
        Produit.quantite_stock <= 0,
    ).scalar() or 0
    alertes = db.session.query(func.count(Produit.id)).filter(
        Produit.is_active == True, Produit.tenant_id == tid,
        Produit.quantite_stock > 0,
        Produit.quantite_stock <= Produit.seuil_alerte,
    ).scalar() or 0
    surstock = db.session.query(func.count(Produit.id)).filter(
        Produit.is_active == True, Produit.tenant_id == tid,
        Produit.quantite_stock > Produit.seuil_alerte * 5,
    ).scalar() or 0
    valeur = db.session.query(
        func.coalesce(func.sum(Produit.quantite_stock * Produit.prix_achat_ht), 0)
    ).filter(
        Produit.is_active == True, Produit.tenant_id == tid
    ).scalar()

    return {
        'tenant_id': tid, 'nb_produits': int(total),
        'ruptures': int(ruptures), 'alertes': int(alertes), 'surstock': int(surstock),
        'valeur_stock_achat': round(float(valeur or 0), 2),
        'data_sufficient': int(total) > 0,
    }


def get_stock_turnover(tenant_id=None, days=30, limit=20):
    """Rotation des produits : forte / faible rotation sur la période."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None:
        return no_tenant_result()
    days = max(1, min(int(days or 30), 365))
    limit = max(1, min(int(limit or 20), 50))
    start = datetime.utcnow() - timedelta(days=days)

    rows = db.session.query(
        LigneVente.produit_id, Produit.nom,
        func.sum(LigneVente.quantite).label('qte_vendue'),
    ).join(Vente, LigneVente.vente_id == Vente.id).join(
        Produit, LigneVente.produit_id == Produit.id
    ).filter(
        LigneVente.is_active == True, LigneVente.tenant_id == tid,
        Vente.is_active == True, Vente.tenant_id == tid,
        Vente.statut.in_(SALES_STATUTS_VALIDES), Vente.date >= start,
    ).group_by(LigneVente.produit_id, Produit.nom).all()

    items = []
    for r in rows:
        p = db.session.query(Produit).filter(
            Produit.id == r.produit_id, Produit.tenant_id == tid
        ).first()
        stock = float(p.quantite_stock or 0) if p else 0.0
        qte = float(r.qte_vendue or 0)
        rotation = qte / stock if stock > 0 else (qte if qte > 0 else 0.0)
        items.append({
            'produit_id': r.produit_id, 'nom': r.nom,
            'quantite_vendue': qte, 'stock_actuel': stock,
            'rotation': round(rotation, 3),
        })
    items.sort(key=lambda x: x['rotation'], reverse=True)
    return {'tenant_id': tid, 'days': days,
            'forte_rotation': items[:limit], 'faible_rotation': list(reversed(items[-limit:])),
            'data_sufficient': len(items) > 0}


# === AI_TOOLS_PART4 ===


def get_customer_debts(tenant_id=None, limit=50):
    """Créances clients : factures non payées / payées partiellement avec solde."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None:
        return no_tenant_result()
    limit = max(1, min(int(limit or 50), 100))

    factures = Facture.query.filter(
        Facture.is_active == True, Facture.tenant_id == tid,
        Facture.statut.in_(['non_payee', 'payee_partiel']),
    ).order_by(Facture.created_at.asc()).limit(limit).all()

    items = []; total_du = 0.0
    for f in factures:
        paiements = Paiement.query.filter(
            Paiement.is_active == True, Paiement.tenant_id == tid,
            Paiement.facture_id == f.id, Paiement.statut.in_(PAID_STATUTS),
        ).all()
        paye = sum(float(p.montant or 0) for p in paiements)
        du = float(f.total_ttc or 0) - paye
        if du <= 0:
            continue
        total_du += du
        client = db.session.query(Client).filter(
            Client.id == f.client_id, Client.tenant_id == tid
        ).first()
        items.append({
            'facture_id': f.id, 'reference': f.reference,
            'client_id': f.client_id,
            'client_nom': (client.raison_sociale or client.nom) if client else None,
            'montant_ttc': round(float(f.total_ttc or 0), 2),
            'montant_paye': round(paye, 2), 'montant_du': round(du, 2),
            'date_facture': f.created_at.isoformat() if f.created_at else None,
        })
    items.sort(key=lambda x: x['montant_du'], reverse=True)
    return {'tenant_id': tid, 'items': items, 'count': len(items),
            'total_creances': round(total_du, 2), 'data_sufficient': True}


def get_pending_invoices(tenant_id=None, limit=50):
    """Factures en attente de paiement avec ancienneté."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None:
        return no_tenant_result()
    limit = max(1, min(int(limit or 50), 100))
    today = datetime.utcnow().date()

    factures = Facture.query.filter(
        Facture.is_active == True, Facture.tenant_id == tid,
        Facture.statut.in_(['non_payee', 'payee_partiel']),
    ).order_by(Facture.created_at.asc()).limit(limit).all()

    items = []; total = 0.0
    for f in factures:
        created = f.created_at.date() if f.created_at and hasattr(f.created_at, 'date') else None
        age = (today - created).days if created else 0
        total += float(f.total_ttc or 0)
        items.append({
            'facture_id': f.id, 'reference': f.reference,
            'client_id': f.client_id, 'montant_ttc': round(float(f.total_ttc or 0), 2),
            'anciennete_jours': age,
        })
    return {'tenant_id': tid, 'items': items, 'count': len(items),
            'total_attente': round(total, 2), 'data_sufficient': True}


# === AI_TOOLS_PART5 ===


def get_supplier_price_changes(tenant_id=None, days=180, threshold_pct=5.0):
    """Détection de hausse/baisse des prix d'achat par produit/fournisseur."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None:
        return no_tenant_result()
    days = max(30, min(int(days or 180), 730))
    start = datetime.utcnow() - timedelta(days=days)
    mid = start + timedelta(days=days / 2)

    rows = db.session.query(
        LigneAchat.produit_id, LigneAchat.prix_unitaire_ht,
        CommandeAchat.fournisseur_id, CommandeAchat.date_commande,
    ).join(CommandeAchat, LigneAchat.commande_achat_id == CommandeAchat.id).filter(
        LigneAchat.is_active == True, LigneAchat.tenant_id == tid,
        CommandeAchat.is_active == True, CommandeAchat.tenant_id == tid,
        CommandeAchat.date_commande >= start,
    ).all()

    buckets = {}
    for r in rows:
        if not r.date_commande or r.prix_unitaire_ht is None:
            continue
        key = (r.produit_id, r.fournisseur_id)
        period = 'recent' if r.date_commande >= mid else 'ancien'
        buckets.setdefault(key, {'recent': [], 'ancien': []})
        buckets[key][period].append(float(r.prix_unitaire_ht))

    changes = []
    for (pid, fid), b in buckets.items():
        if not b['ancien'] or not b['recent']:
            continue
        moy_ancien = sum(b['ancien']) / len(b['ancien'])
        moy_recent = sum(b['recent']) / len(b['recent'])
        if moy_ancien <= 0:
            continue
        evol = ((moy_recent - moy_ancien) / moy_ancien) * 100
        if abs(evol) >= threshold_pct:
            produit = db.session.query(Produit).filter(
                Produit.id == pid, Produit.tenant_id == tid).first()
            fournisseur = db.session.query(Fournisseur).filter(
                Fournisseur.id == fid, Fournisseur.tenant_id == tid).first()
            changes.append({
                'produit_id': pid, 'produit_nom': produit.nom if produit else None,
                'fournisseur_id': fid,
                'fournisseur_nom': fournisseur.raison_sociale if fournisseur else None,
                'prix_moyen_ancien': round(moy_ancien, 2),
                'prix_moyen_recent': round(moy_recent, 2),
                'evolution_pct': round(evol, 1),
                'nb_achats_ancien': len(b['ancien']),
                'nb_achats_recent': len(b['recent']),
            })
    changes.sort(key=lambda x: abs(x['evolution_pct']), reverse=True)
    return {'tenant_id': tid, 'days': days, 'items': changes, 'count': len(changes),
            'data_sufficient': len(changes) > 0}


def get_pending_purchase_orders(tenant_id=None, limit=20):
    """Commandes fournisseurs en cours (non reçues / non annulées)."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None:
        return no_tenant_result()
    limit = max(1, min(int(limit or 20), 50))
    today = datetime.utcnow().date()

    commandes = CommandeAchat.query.filter(
        CommandeAchat.is_active == True, CommandeAchat.tenant_id == tid,
        CommandeAchat.statut.in_([
            StatutCommandeAchat.BROUILLON, StatutCommandeAchat.ENVOYEE,
            StatutCommandeAchat.CONFIRMEE,
        ]),
    ).order_by(CommandeAchat.date_commande.asc()).limit(limit).all()

    items = []
    for c in commandes:
        date_cmd = c.date_commande.date() if c.date_commande and hasattr(c.date_commande, 'date') else None
        age = (today - date_cmd).days if date_cmd else 0
        fournisseur = db.session.query(Fournisseur).filter(
            Fournisseur.id == c.fournisseur_id, Fournisseur.tenant_id == tid).first()
        items.append({
            'commande_id': c.id, 'reference': c.reference,
            'fournisseur_id': c.fournisseur_id,
            'fournisseur_nom': fournisseur.raison_sociale if fournisseur else None,
            'statut': c.statut.value if hasattr(c.statut, 'value') else str(c.statut),
            'total_ttc': round(float(c.total_ttc or 0), 2),
            'date_commande': c.date_commande.isoformat() if c.date_commande else None,
            'anciennete_jours': age,
        })
    return {'tenant_id': tid, 'items': items, 'count': len(items),
            'data_sufficient': True}


# === AI_TOOLS_PART6 ===


def get_clients_summary(tenant_id=None, days=90, limit=10):
    """Synthèse clients : nombre total, top clients par CA."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None:
        return no_tenant_result()
    days = max(1, min(int(days or 90), 365))
    limit = max(1, min(int(limit or 10), 30))
    start = datetime.utcnow() - timedelta(days=days)

    total = db.session.query(func.count(Client.id)).filter(
        Client.is_active == True, Client.tenant_id == tid
    ).scalar() or 0

    rows = db.session.query(
        Vente.client_id,
        func.count(Vente.id).label('nb'),
        func.coalesce(func.sum(Vente.total_ttc), 0).label('ca'),
    ).filter(
        Vente.is_active == True, Vente.tenant_id == tid,
        Vente.statut.in_(SALES_STATUTS_VALIDES), Vente.date >= start,
    ).group_by(Vente.client_id).order_by(
        func.sum(Vente.total_ttc).desc()
    ).limit(limit).all()

    top = []
    for r in rows:
        client = db.session.query(Client).filter(
            Client.id == r.client_id, Client.tenant_id == tid).first()
        top.append({
            'client_id': r.client_id,
            'nom': (client.raison_sociale or client.nom) if client else None,
            'nb_ventes': int(r.nb or 0), 'ca_ttc': round(float(r.ca or 0), 2),
        })
    return {'tenant_id': tid, 'days': days, 'nb_clients': int(total),
            'top_clients': top, 'data_sufficient': int(total) > 0}


def get_suppliers_summary(tenant_id=None, days=180, limit=10):
    """Synthèse fournisseurs : nombre total, plus utilisés, délais moyens."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None:
        return no_tenant_result()
    days = max(30, min(int(days or 180), 730))
    limit = max(1, min(int(limit or 10), 30))
    start = datetime.utcnow() - timedelta(days=days)

    total = db.session.query(func.count(Fournisseur.id)).filter(
        Fournisseur.is_active == True, Fournisseur.tenant_id == tid
    ).scalar() or 0

    rows = db.session.query(
        CommandeAchat.fournisseur_id,
        func.count(CommandeAchat.id).label('nb'),
        func.coalesce(func.sum(CommandeAchat.total_ttc), 0).label('total'),
    ).filter(
        CommandeAchat.is_active == True, CommandeAchat.tenant_id == tid,
        CommandeAchat.date_commande >= start,
    ).group_by(CommandeAchat.fournisseur_id).order_by(
        func.count(CommandeAchat.id).desc()
    ).limit(limit).all()

    top = []
    for r in rows:
        f = db.session.query(Fournisseur).filter(
            Fournisseur.id == r.fournisseur_id, Fournisseur.tenant_id == tid).first()
        top.append({
            'fournisseur_id': r.fournisseur_id,
            'nom': f.raison_sociale if f else None,
            'nb_commandes': int(r.nb or 0),
            'total_ttc': round(float(r.total or 0), 2),
            'delai_livraison_jours': f.delai_livraison if f else None,
        })
    return {'tenant_id': tid, 'days': days, 'nb_fournisseurs': int(total),
            'top_fournisseurs': top, 'data_sufficient': int(total) > 0}


def get_products_dormant(tenant_id=None, days=60, limit=20):
    """Produits sans vente sur la période (produits dormants)."""
    tid = resolve_tenant_id(tenant_id)
    if tid is None:
        return no_tenant_result()
    days = max(7, min(int(days or 60), 365))
    limit = max(1, min(int(limit or 20), 50))
    start = datetime.utcnow() - timedelta(days=days)

    vendus = db.session.query(LigneVente.produit_id).join(
        Vente, LigneVente.vente_id == Vente.id
    ).filter(
        LigneVente.is_active == True, LigneVente.tenant_id == tid,
        Vente.is_active == True, Vente.tenant_id == tid,
        Vente.statut.in_(SALES_STATUTS_VALIDES), Vente.date >= start,
    ).distinct().subquery()

    dormants = Produit.query.filter(
        Produit.is_active == True, Produit.tenant_id == tid,
        ~Produit.id.in_(db.session.query(vendus.c.produit_id)),
    ).order_by(Produit.quantite_stock.desc()).limit(limit).all()

    items = [{
        'produit_id': p.id, 'nom': p.nom, 'reference': p.reference,
        'stock_actuel': float(p.quantite_stock or 0),
    } for p in dormants]
    return {'tenant_id': tid, 'days': days, 'items': items, 'count': len(items),
            'data_sufficient': True}
