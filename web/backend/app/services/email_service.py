# -*- coding: utf-8 -*-
# app/services/email_service.py
# Système de mailing supprimé : mot de passe envoyé directement à l'imprimante.

logger = __import__('logging').getLogger(__name__)

def send_email(subject, html_body, recipient, *, config=None):
    logger.info('[EMAIL DESACTIVE] Pas d\'envoi : recipient=%s subject=%s', recipient, subject)
    return {'success': True, 'recipient': recipient, 'delivered': False}

def send_welcome_email(user, tenant, temporary_password, *, app_url=None):
    logger.info('[EMAIL DESACTIVE] Mot de passe temporaire pour impression : %s / %s', getattr(user, 'email', ''), temporary_password)
    return {'success': True, 'delivered': False, 'temporary_password_for_print': temporary_password}

def send_password_reset_email(user, tenant, raw_token, *, expires_in_minutes=30, app_url=None):
    logger.info('[EMAIL DESACTIVE] Reset password non envoyé')
    return {'success': True, 'delivered': False}

def send_password_changed_email(user, tenant, *, changed_at=None, app_url=None):
    logger.info('[EMAIL DESACTIVE] Changement mot de passe non envoyé')
    return {'success': True, 'delivered': False}

def send_invoice_email(invoice_id, recipient_email, smtp_config=None):
    logger.info('[EMAIL DESACTIVE] Facture #%s non envoyée', invoice_id)
    return {'success': True, 'delivered': False}

def send_payment_confirmation(payment_id, recipient_email, smtp_config=None):
    logger.info('[EMAIL DESACTIVE] Confirmation paiement #%s non envoyée', payment_id)
    return {'success': True, 'delivered': False}

def send_stock_alert(product_id, threshold, recipient_email, smtp_config=None):
    logger.info('[EMAIL DESACTIVE] Alerte stock produit #%s non envoyée', product_id)
    return {'success': True, 'delivered': False}
