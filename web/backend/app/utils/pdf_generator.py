import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from app.config.settings import Config

GOLD = colors.HexColor('#d4af37')
ONYX = colors.HexColor('#111111')
ONYX_SOFT = colors.HexColor('#2a2a2a')
MUTED = colors.HexColor('#77776f')
LINE = colors.HexColor('#e6e6e1')
BEIGE = colors.HexColor('#f7f7f5')
WHITE = colors.white


def _get_upload_folder():
    return Config.UPLOAD_FOLDER


def _build_styles():
    base = getSampleStyleSheet()

    styles = {}

    styles['tenant_name'] = ParagraphStyle(
        'tenant_name',
        parent=base['Heading1'],
        fontSize=20,
        leading=24,
        textColor=ONYX,
        fontName='Helvetica-Bold',
        spaceAfter=2,
    )
    styles['tenant_info'] = ParagraphStyle(
        'tenant_info',
        parent=base['Normal'],
        fontSize=9,
        leading=13,
        textColor=MUTED,
        fontName='Helvetica',
    )
    styles['doc_title'] = ParagraphStyle(
        'doc_title',
        parent=base['Heading1'],
        fontSize=22,
        leading=26,
        textColor=ONYX,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    styles['doc_ref'] = ParagraphStyle(
        'doc_ref',
        parent=base['Normal'],
        fontSize=10,
        leading=14,
        textColor=MUTED,
        fontName='Helvetica',
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    styles['section_label'] = ParagraphStyle(
        'section_label',
        parent=base['Normal'],
        fontSize=9,
        leading=12,
        textColor=ONYX,
        fontName='Helvetica-Bold',
        spaceAfter=4,
        textTransform='uppercase',
        letterSpacing=0.08,
    )
    styles['normal'] = ParagraphStyle(
        'normal',
        parent=base['Normal'],
        fontSize=10,
        leading=14,
        textColor=ONYX,
        fontName='Helvetica',
    )
    styles['normal_right'] = ParagraphStyle(
        'normal_right',
        parent=base['Normal'],
        fontSize=10,
        leading=14,
        textColor=ONYX,
        fontName='Helvetica',
        alignment=TA_RIGHT,
    )
    styles['small'] = ParagraphStyle(
        'small',
        parent=base['Normal'],
        fontSize=8,
        leading=11,
        textColor=MUTED,
        fontName='Helvetica',
    )
    styles['footer'] = ParagraphStyle(
        'footer',
        parent=base['Normal'],
        fontSize=8,
        leading=10,
        textColor=MUTED,
        fontName='Helvetica',
        alignment=TA_CENTER,
    )
    styles['total'] = ParagraphStyle(
        'total',
        parent=base['Normal'],
        fontSize=11,
        leading=15,
        textColor=ONYX,
        fontName='Helvetica-Bold',
        alignment=TA_RIGHT,
    )
    styles['table_header'] = ParagraphStyle(
        'table_header',
        parent=base['Normal'],
        fontSize=9,
        leading=12,
        textColor=WHITE,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
    )
    styles['table_cell'] = ParagraphStyle(
        'table_cell',
        parent=base['Normal'],
        fontSize=9,
        leading=12,
        textColor=ONYX,
        fontName='Helvetica',
        alignment=TA_LEFT,
    )
    styles['table_cell_right'] = ParagraphStyle(
        'table_cell_right',
        parent=base['Normal'],
        fontSize=9,
        leading=12,
        textColor=ONYX,
        fontName='Helvetica',
        alignment=TA_RIGHT,
    )
    styles['table_cell_center'] = ParagraphStyle(
        'table_cell_center',
        parent=base['Normal'],
        fontSize=9,
        leading=12,
        textColor=ONYX,
        fontName='Helvetica',
        alignment=TA_CENTER,
    )
    return styles


def _add_header_footer(canvas_obj, doc, tenant, doc_title, doc_ref, page_count=1):
    canvas_obj.saveState()
    try:
        width, height = A4
        margin = 2 * cm

        canvas_obj.setStrokeColor(LINE)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(margin, height - margin + 0.4 * cm, width - margin, height - margin + 0.4 * cm)

        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.setFillColor(MUTED)
        canvas_obj.drawRightString(width - margin, 1.2 * cm, f'Page {doc.page} / {page_count}')

        if tenant:
            canvas_obj.setFont('Helvetica', 7)
            canvas_obj.setFillColor(MUTED)
            footer_text = f"{tenant.get('nom', '')} | {tenant.get('adresse', '')}, {tenant.get('ville', '')} | {tenant.get('telephone', '')} | {tenant.get('email_contact', '')}"
            canvas_obj.drawString(margin, 1.2 * cm, footer_text[:120])

        canvas_obj.setStrokeColor(LINE)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(margin, margin - 0.3 * cm, width - margin, margin - 0.3 * cm)
    except Exception:
        pass
    canvas_obj.restoreState()


def _try_load_logo(logo_path_or_url, max_width_cm=4):
    try:
        if not logo_path_or_url:
            return None
        path = logo_path_or_url
        if not os.path.isabs(path):
            folder = _get_upload_folder()
            candidate = os.path.join(folder, path)
            if os.path.exists(candidate):
                path = candidate
        if os.path.exists(path):
            img = ImageReader(path)
            iw, ih = img.getSize()
            aspect = ih / float(iw)
            max_w = max_width_cm * cm
            w = min(max_w, iw)
            h = w * aspect
            if h > 3 * cm:
                h = 3 * cm
                w = h / aspect
            return Image(path, width=w, height=h)
    except Exception:
        return None
    return None


def _build_table_header(styles):
    return [
        Paragraph('Désignation', styles['table_header']),
        Paragraph('Qté', styles['table_header']),
        Paragraph('Prix unit. HT', styles['table_header']),
        Paragraph('TVA', styles['table_header']),
        Paragraph('Total HT', styles['table_header']),
    ]


def _build_table_row(styles, item):
    return [
        Paragraph(str(item.get('produit_nom', item.get('designation', item.get('description', '')))), styles['table_cell']),
        Paragraph(str(item.get('quantite', item.get('qte', ''))), styles['table_cell_center']),
        Paragraph(f"{float(item.get('prix_unitaire', item.get('prix_ht', 0))):.2f}", styles['table_cell_right']),
        Paragraph(f"{item.get('taux_tva', item.get('tva', 0))}%", styles['table_cell_center']),
        Paragraph(f"{float(item.get('total_ht', item.get('total', 0))):.2f}", styles['table_cell_right']),
    ]


def generate_document_pdf(filename, type_document, reference, donnees, tenant, modele=None):
    folder = _get_upload_folder()
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)

    styles = _build_styles()
    width, height = A4
    margin = 2 * cm
    content_width = width - 2 * margin

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin + 1.6 * cm,
        bottomMargin=margin + 1.6 * cm,
    )

    story = []
    logo = None
    if modele and modele.get('logo_url'):
        logo = _try_load_logo(modele.get('logo_url'))
    if not logo and tenant and tenant.get('logo'):
        logo = _try_load_logo(tenant.get('logo'))

    tenant_name = tenant.get('nom', '') if tenant else ''
    tenant_adresse = tenant.get('adresse', '') if tenant else ''
    tenant_ville = tenant.get('ville', '') if tenant else ''
    tenant_pays = tenant.get('pays', '') if tenant else ''
    tenant_telephone = tenant.get('telephone', '') if tenant else ''
    tenant_email = tenant.get('email_contact', '') if tenant else ''
    tenant_devise = tenant.get('devise', 'MGA') if tenant else 'MGA'

    if logo:
        story.append(logo)
        story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph(tenant_name or 'ENTREPRISE', styles['tenant_name']))
    if tenant_adresse or tenant_ville or tenant_telephone or tenant_email:
        info_line = ', '.join(filter(None, [tenant_adresse, tenant_ville, tenant_pays, tenant_telephone, tenant_email]))
        story.append(Paragraph(info_line, styles['tenant_info']))
    story.append(Spacer(1, 0.3 * cm))

    story.append(HRFlowable(width=content_width, thickness=1.5, color=GOLD, spaceAfter=0.4 * cm))

    type_labels = {
        'facture': 'FACTURE',
        'devis': 'DEVIS',
        'contrat': 'CONTRAT',
        'bon_livraison': 'BON DE LIVRAISON',
        'avoir': 'AVOIR',
    }
    title = type_labels.get(type_document, type_document.upper())
    story.append(Paragraph(title, styles['doc_title']))
    story.append(Paragraph(f'Référence : {reference}', styles['doc_ref']))
    story.append(Spacer(1, 0.4 * cm))

    client_nom = donnees.get('client_nom', donnees.get('client', ''))
    client_adresse = donnees.get('client_adresse', '')
    client_ville = donnees.get('client_ville', '')
    client_email = donnees.get('client_email', '')
    client_telephone = donnees.get('client_telephone', '')

    if client_nom or client_adresse or client_email:
        story.append(Paragraph('CLIENT', styles['section_label']))
        client_lines = ' | '.join(filter(None, [client_nom, client_adresse, client_ville, client_email, client_telephone]))
        story.append(Paragraph(client_lines or '-', styles['normal']))
        story.append(Spacer(1, 0.3 * cm))

    items = donnees.get('items', donnees.get('lignes', []))
    if not items and isinstance(donnees, list):
        items = donnees

    if items:
        story.append(Paragraph('DÉTAIL', styles['section_label']))
        story.append(Spacer(1, 0.1 * cm))

        table_data = [_build_table_header(styles)]
        for item in items:
            table_data.append(_build_table_row(styles, item))

        table = Table(table_data, colWidths=[content_width * 0.38, content_width * 0.12, content_width * 0.18, content_width * 0.12, content_width * 0.20], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ONYX),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), BEIGE),
            ('GRID', (0, 0), (-1, -1), 0.5, LINE),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.4 * cm))

    total_ht = float(donnees.get('total_ht', donnees.get('total', 0)))
    taux_tva = float(donnees.get('taux_tva', 0))
    total_ttc = float(donnees.get('total_ttc', total_ht * (1 + taux_tva / 100)))
    remise = float(donnees.get('remise', 0))
    net_ht = total_ht - remise
    total_tva = net_ht * taux_tva / 100 if taux_tva else 0
    net_ttc = net_ht + total_tva

    story.append(HRFlowable(width=content_width, thickness=0.5, color=LINE, spaceAfter=0.3 * cm))

    totals_data = [
        [Paragraph('Total HT', styles['normal']), Paragraph(f'{total_ht:.2f} {tenant_devise}', styles['normal_right'])],
        [Paragraph('Remise', styles['normal']), Paragraph(f'{remise:.2f} {tenant_devise}', styles['normal_right'])],
        [Paragraph('Net HT', styles['normal']), Paragraph(f'{net_ht:.2f} {tenant_devise}', styles['normal'])],
        [Paragraph(f'TVA ({taux_tva:.1f}%)', styles['normal']), Paragraph(f'{total_tva:.2f} {tenant_devise}', styles['normal_right'])],
        [Paragraph('TOTAL TTC', styles['total']), Paragraph(f'{net_ttc:.2f} {tenant_devise}', styles['total'])],
    ]
    totals_table = Table(totals_data, colWidths=[content_width * 0.7, content_width * 0.3])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, ONYX),
        ('BACKGROUND', (0, -1), (-1, -1), BEIGE),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 0.6 * cm))

    if modele and modele.get('conditions_generales'):
        story.append(Paragraph('CONDITIONS GÉNÉRALES', styles['section_label']))
        story.append(Paragraph(modele.get('conditions_generales', ''), styles['small']))
        story.append(Spacer(1, 0.3 * cm))

    if modele and modele.get('mention_legales'):
        story.append(Paragraph('MENTIONS LÉGALES', styles['section_label']))
        story.append(Paragraph(modele.get('mention_legales', ''), styles['small']))

    page_count = 1

    def _on_page(canvas_obj, doc_obj):
        nonlocal page_count
        page_count = max(page_count, doc_obj.page)
        _add_header_footer(canvas_obj, doc_obj, tenant, title, reference, page_count)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return filepath


def generate_report_pdf(filename, data, title):
    folder = _get_upload_folder()
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = _build_styles()
    story = []
    story.append(Paragraph(title, styles['doc_title']))
    story.append(Spacer(1, 0.5 * cm))
    if isinstance(data, list):
        table_data = [_build_table_header(styles)] if data else [['Aucune donnée', '', '', '', '']]
        for row in data:
            table_data.append(_build_table_row(styles, row if isinstance(row, dict) else {'produit_nom': str(row)}))
        table = Table(table_data, colWidths=[doc.width * 0.38, doc.width * 0.12, doc.width * 0.18, doc.width * 0.12, doc.width * 0.20], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ONYX),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, LINE),
            ('BACKGROUND', (0, 1), (-1, -1), BEIGE),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
    else:
        for key, value in data.items() if isinstance(data, dict) else []:
            story.append(Paragraph(f"{key}: {value}", styles['normal']))
    doc.build(story)
    return filepath


def generate_invoice_pdf(filename, invoice_data):
    type_document = invoice_data.get('type_document', 'facture')
    reference = invoice_data.get('reference', '')
    donnees = invoice_data.get('donnees', invoice_data)
    tenant = invoice_data.get('tenant', {})
    modele = invoice_data.get('modele', {})
    return generate_document_pdf(filename, type_document, reference, donnees, tenant, modele)


def generate_quote_pdf(filename, quote_data):
    type_document = quote_data.get('type_document', 'devis')
    reference = quote_data.get('reference', '')
    donnees = quote_data.get('donnees', quote_data)
    tenant = quote_data.get('tenant', {})
    modele = quote_data.get('modele', {})
    return generate_document_pdf(filename, type_document, reference, donnees, tenant, modele)
