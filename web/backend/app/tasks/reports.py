from app.utils.pdf_generator import generate_report_pdf
from app.utils.excel_generator import generate_excel_report
from app.models.vente import Vente
from app.models.produit import Produit
from app.security.tenant import get_current_tenant_id
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func

def generate_daily_sales_report(date_str, tenant_id):
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    query = Vente.query.filter(
        Vente.is_active == True,
        Vente.created_at >= target_date,
        Vente.created_at < target_date + timedelta(days=1)
    )
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    sales = query.all()
    data = [{'id': s.id, 'reference': s.reference, 'total_ttc': float(s.total_ttc), 'statut': s.statut} for s in sales]
    filename = f'report_sales_{date_str}.pdf'
    return generate_report_pdf(filename, data, f'Rapport des ventes du {date_str}')

def generate_monthly_report(month, year, tenant_id):
    query = Vente.query.filter(
        Vente.is_active == True,
        Vente.created_at >= datetime(year, month, 1),
        Vente.created_at < datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
    )
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    sales = query.all()
    total = sum(float(s.total_ttc) for s in sales)
    data = [{'total_ventes': len(sales), 'ca_total': total, 'mois': month, 'annee': year}]
    filename = f'report_monthly_{year}_{month:02d}.pdf'
    return generate_report_pdf(filename, data, f'Rapport mensuel {month}/{year}')

def generate_stock_report(tenant_id):
    query = Produit.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    products = query.all()
    data = [{'reference': p.reference, 'nom': p.nom, 'stock': float(p.quantite_stock), 'valeur': float(p.valeur_stock)} for p in products]
    filename = 'report_stock.pdf'
    return generate_report_pdf(filename, data, 'Rapport de stock')