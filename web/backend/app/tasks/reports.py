from app.utils.pdf_generator import generate_report_pdf
from app.utils.excel_generator import generate_excel_report
from app.models.vente import Vente
from app.models.produit import Produit
from app.security.tenant import get_current_tenant_id
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def generate_daily_sales_report(date_str, tenant_id):
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        raise ValueError("date_str invalide (attendu YYYY-MM-DD)")
    query = Vente.query.filter(
        Vente.is_active == True,
        Vente.created_at >= target_date,
        Vente.created_at < target_date + timedelta(days=1)
    )
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    sales = query.all()
    data = [
        {
            'id': s.id,
            'reference': s.reference,
            'total_ttc': _safe_float(s.total_ttc),
            'statut': str(s.statut) if s.statut else '',
        }
        for s in sales
    ]
    filename = f'report_sales_{date_str}.pdf'
    return generate_report_pdf(filename, data, f'Rapport des ventes du {date_str}')


def generate_monthly_report(month, year, tenant_id):
    try:
        month = int(month)
        year = int(year)
    except (ValueError, TypeError):
        raise ValueError("month/year doivent être des entiers")
    start = datetime(year, month, 1)
    if month < 12:
        end = datetime(year, month + 1, 1)
    else:
        end = datetime(year + 1, 1, 1)
    query = Vente.query.filter(
        Vente.is_active == True,
        Vente.created_at >= start,
        Vente.created_at < end
    )
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    sales = query.all()
    total = sum(_safe_float(s.total_ttc) for s in sales)
    data = [{'total_ventes': len(sales), 'ca_total': total, 'mois': month, 'annee': year}]
    filename = f'report_monthly_{year}_{month:02d}.pdf'
    return generate_report_pdf(filename, data, f'Rapport mensuel {month}/{year}')


def generate_stock_report(tenant_id):
    query = Produit.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    products = query.all()
    data = [
        {
            'reference': p.reference,
            'nom': p.nom,
            'stock': _safe_float(p.quantite_stock),
            'valeur': _safe_float(p.valeur_stock),
        }
        for p in products
    ]
    filename = 'report_stock.pdf'
    return generate_report_pdf(filename, data, 'Rapport de stock')