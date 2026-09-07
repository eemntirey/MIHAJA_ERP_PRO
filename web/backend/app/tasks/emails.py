import smtplib
import logging
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def send_email(recipient, subject, body, smtp_config=None):
    if not recipient:
        return {' : 'error', 'message': 'Destinataire manquant'}
    if not smtp_config:
        smtp_config = {
            'host': 'localhost',
            'port': 25,
            'user': None,
            'password': None,
            'use_tls': False,
            'timeout': 10,
        }
    msg = MIMEMultipart()
    msg['From'] = smtp_config.get('user') or smtp_config.get('from', 'erp@localhost')
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    host = smtp_config.get('host')
    port = int(smtp_config.get('port', 25))
    timeout = int(smtp_config.get('timeout', 10))
    user = smtp_config.get('user')
    password = smtp_config.get('password')
    use_tls = bool(smtp_config.get('use_tls', port == 587))

    try:
        with smtplib.SMTP(host, port, timeout=timeout) as server:
            server.ehlo()
            if use_tls:
                # starttls + mot de passe : on chiffré la connexion pour ne
                # plus faire circuler les credentials et le contenu en clair.
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
            if user:
                server.login(user, password or '')
            server.send_message(msg)
        return {' : 'sent', 'recipient': recipient}
    except Exception as exc:
        logger.exception('Echec envoi email a %s', recipient)
        return {' : 'error', 'message': str(exc), 'recipient': recipient}


def send_invoice_email(invoice_id, recipient_email, smtp_config=None):
    if not recipient_email:
        return {' : 'error', 'message': 'Destinataire manquant'}
    return send_email(
        recipient_email,
        f'Facture #{invoice_id}',
        f'<p>Votre facture #{invoice_id} est disponible.</p>',
        smtp_config,
    )


def send_payment_confirmation(payment_id, recipient_email, smtp_config=None):
    if not recipient_email:
        return {' : 'error', 'message': 'Destinataire manquant'}
    return send_email(
        recipient_email,
        f'Confirmation paiement #{payment_id}',
        f'<p>Paiement #{payment_id} confirmé.</p>',
        smtp_config,
    )


def send_stock_alert(product_id, threshold, recipient_email, smtp_config=None):
    if not recipient_email:
        return {' : 'error', 'message': 'Destinataire manquant'}
    return send_email(
        recipient_email,
        f'Alerte stock produit #{product_id}',
        f'<p>Le produit #{product_id} a atteint le seuil de {threshold}.</p>',
        smtp_config,
    )