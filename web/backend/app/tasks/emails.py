import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(recipient, subject, body, smtp_config=None):
    if not smtp_config:
        smtp_config = {
            'host': 'localhost',
            'port': 25,
            'user': None,
            'password': None
        }
    msg = MIMEMultipart()
    msg['From'] = smtp_config.get('user', 'erp@localhost')
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
        if smtp_config.get('user'):
            server.login(smtp_config['user'], smtp_config['password'])
        server.send_message(msg)
    return {'status': 'sent', 'recipient': recipient}

def send_invoice_email(invoice_id, recipient_email, smtp_config=None):
    return send_email(recipient_email, f'Facture #{invoice_id}', f'<p>Votre facture #{invoice_id} est disponible.</p>', smtp_config)

def send_payment_confirmation(payment_id, smtp_config=None):
    return send_email('client@example.com', f'Confirmation paiement #{payment_id}', f'<p>Paiement #{payment_id} confirmé.</p>', smtp_config)

def send_stock_alert(product_id, threshold, smtp_config=None):
    return send_email('stock@example.com', f'Alerte stock produit #{product_id}', f'<p>Le produit #{product_id} a atteint le seuil de {threshold}.</p>', smtp_config)