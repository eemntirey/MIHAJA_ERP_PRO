import pandas as pd
import numpy as np
from datetime import datetime
from app.models.stock import MouvementStock
from app.models.vente import Vente
from app.models.facture import Facture
from app.models.produit import Produit
from app.security.tenant import get_current_tenant_id
from app import db


def detect_stock_anomalies(tenant_id=None):
    tenant_id = get_current_tenant_id() or tenant_id
    mouvements = MouvementStock.query.filter_by(is_active=True)
    if tenant_id:
        mouvements = mouvements.filter_by(tenant_id=tenant_id)
    mouvements = mouvements.all()

    if not mouvements:
        return {'anomalies': [], 'count': 0}

    data = []
    for m in mouvements:
        date_str = m.created_at.isoformat() if hasattr(m.created_at, 'isoformat') else str(m.created_at)
        data.append({
            'date': date_str,
            'quantite': abs(float(m.quantite or 0)),
            'produit_id': m.produit_id
        })

    df = pd.DataFrame(data)
    anomalies = []

    for produit_id in df['produit_id'].unique():
        prod_df = df[df['produit_id'] == produit_id]
        if len(prod_df) < 2:
            continue
        mean_qty = prod_df['quantite'].mean()
        std_qty = prod_df['quantite'].std()

        produit_query = Produit.query.filter_by(id=int(produit_id))
        if tenant_id:
            produit_query = produit_query.filter_by(tenant_id=tenant_id)
        produit = produit_query.first()
        nom_produit = produit.nom if produit else f"Produit #{produit_id}"

        if std_qty == 0 or np.isnan(std_qty):
            continue

        for _, row in prod_df.iterrows():
            z_score = abs(row['quantite'] - mean_qty) / std_qty
            if z_score > 1.8:
                anomalies.append({
                    'produit_id': int(produit_id),
                    'nom_produit': nom_produit,
                    'date': row['date'],
                    'quantite': row['quantite'],
                    'mean': round(mean_qty, 2),
                    'z_score': round(z_score, 2),
                    'type': 'Variation anormale de stock',
                    'severity': 'high' if z_score > 2.5 else 'medium'
                })

    return {'anomalies': anomalies, 'count': len(anomalies)}


def detect_sales_anomalies(tenant_id=None):
    tenant_id = get_current_tenant_id() or tenant_id
    ventes = Vente.query.filter_by(is_active=True)
    if tenant_id:
        ventes = ventes.filter_by(tenant_id=tenant_id)
    ventes = ventes.all()

    if not ventes:
        return {'anomalies': [], 'count': 0}

    data = []
    for v in ventes:
        date_str = v.created_at.isoformat() if hasattr(v.created_at, 'isoformat') else str(v.created_at)
        data.append({
            'id': v.id,
            'reference': getattr(v, 'reference', f'Vente #{v.id}'),
            'date': date_str,
            'total_ttc': float(v.total_ttc or 0)
        })

    df = pd.DataFrame(data)
    anomalies = []

    mean_val = df['total_ttc'].mean()
    std_val = df['total_ttc'].std()

    if std_val == 0 or np.isnan(std_val):
        return {'anomalies': [], 'count': 0}

    for _, row in df.iterrows():
        z_score = abs(row['total_ttc'] - mean_val) / std_val
        if z_score > 1.8:
            anomalies.append({
                'vente_id': row['id'],
                'reference': row['reference'],
                'date': row['date'],
                'total_ttc': round(row['total_ttc'], 2),
                'mean': round(mean_val, 2),
                'z_score': round(z_score, 2),
                'type': 'Montant de vente inhabituel',
                'severity': 'high' if z_score > 2.5 else 'medium'
            })

    return {'anomalies': anomalies, 'count': len(anomalies)}


def detect_payment_anomalies(tenant_id=None):
    tenant_id = get_current_tenant_id() or tenant_id
    query = Facture.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)

    factures = query.all()
    anomalies = []
    today = datetime.utcnow().date()

    for f in factures:
        statut_val = getattr(f.statut, 'value', str(f.statut)).lower()
        if statut_val in ['non_payee', 'payee_partiel', 'en_attente']:
            if f.created_at:
                created_date = f.created_at.date() if isinstance(f.created_at, datetime) else f.created_at
                days_overdue = (today - created_date).days
                if days_overdue > 30:
                    anomalies.append({
                        'facture_id': f.id,
                        'reference': f.reference,
                        'montant_ttc': float(f.total_ttc or 0),
                        'retard_jours': days_overdue,
                        'statut': statut_val,
                        'type': 'Facture impayée en retard critique',
                        'severity': 'high' if days_overdue > 60 else 'medium'
                    })

    return {'anomalies': anomalies, 'count': len(anomalies)}
