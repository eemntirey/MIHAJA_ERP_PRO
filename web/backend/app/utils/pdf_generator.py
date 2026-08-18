import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

def _get_upload_folder():
    from app.config.settings import Config
    return Config.UPLOAD_FOLDER

def generate_invoice_pdf(filename, invoice_data):
    folder = _get_upload_folder()
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("FACTURE", styles['Title']))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"Référence: {invoice_data.get('reference', '')}", styles['Normal']))
    story.append(Paragraph(f"Client: {invoice_data.get('client_nom', '')}", styles['Normal']))
    story.append(Spacer(1, 1*cm))
    
    data = [['Produit', 'Qté', 'Prix', 'TVA', 'Total']]
    for item in invoice_data.get('items', []):
        data.append([
            item.get('produit_nom', ''),
            str(item.get('quantite', 0)),
            f"{item.get('prix_unitaire', 0):.2f} Ar",
            f"{item.get('taux_tva', 0)}%",
            f"{item.get('total_ht', 0):.2f} Ar"
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(f"Total: {invoice_data.get('total_ht', 0):.2f} Ar", styles['Normal']))
    story.append(Paragraph(f"Total TTC: {invoice_data.get('total_ttc', 0):.2f} Ar", styles['Normal']))
    doc.build(story)
    return filepath

def generate_quote_pdf(filename, quote_data):
    folder = _get_upload_folder()
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("DEVIS", styles['Title']))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"Référence: {quote_data.get('reference', '')}", styles['Normal']))
    story.append(Paragraph(f"Client: {quote_data.get('client_nom', '')}", styles['Normal']))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(f"Montant total: {quote_data.get('total_ttc', 0):.2f} Ar", styles['Normal']))
    story.append(Paragraph("Ce devis est valable 30 jours.", styles['Normal']))
    doc.build(story)
    return filepath

def generate_report_pdf(filename, data, title):
    folder = _get_upload_folder()
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 0.5*cm))
    if isinstance(data, list):
        table_data = [list(data[0].keys())] if data else [['Aucune donnée']]
        for row in data:
            table_data.append(list(str(v) for v in row.values()))
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(table)
    else:
        for key, value in data.items():
            story.append(Paragraph(f"{key}: {value}", styles['Normal']))
    doc.build(story)
    return filepath