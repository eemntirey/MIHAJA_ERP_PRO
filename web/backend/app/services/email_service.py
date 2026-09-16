# -*- coding: utf-8 -*-
# app/services/email_service.py
# Service d'envoi d'emails (SMTP) pour les flux metier : bienvenue avec mot de
# passe temporaire, reset de mot de passe, changement de mot de passe, envoi
# de facture, confirmation de paiement, alerte stock.
#
# Activation : MAIL_ENABLED=true + MAIL_HOST/MAIL_PORT/MAIL_USERNAME/MAIL_PASSWORD.
# Desactive par defaut (MAIL_ENABLED=false) : aucun envoi SMTP accidentel, le
# resultat est alors {'delivered': False, ...} sans exception.

import html
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime

from app.config.settings import Config

logger = logging.getLogger(__name__)

_APP_NAME = 'MIHAJA ERP'


def _build_smtp_config(config=None):
    """Fusionne une config SMTP specifique (dict) avec la config globale."""
    if config:
        return {
            'host': config.get('host') or Config.MAIL_HOST,
            'port': int(config.get('port') or Config.MAIL_PORT),
            'user': config.get('user') or Config.MAIL_USERNAME,
            'password': config.get('password') or Config.MAIL_PASSWORD,
            'use_tls': bool(config.get('use_tls', Config.MAIL_USE_TLS)),
            'from': config.get('from') or Config.MAIL_FROM,
            'from_name': config.get('from_name') or Config.MAIL_FROM_NAME,
            'timeout': int(config.get('timeout') or Config.MAIL_TIMEOUT),
        }
    return {
        'host': Config.MAIL_HOST,
        'port': int(Config.MAIL_PORT),
        'user': Config.MAIL_USERNAME,
        'password': Config.MAIL_PASSWORD,
        'use_tls': bool(Config.MAIL_USE_TLS),
        'from': Config.MAIL_FROM,
        'from_name': Config.MAIL_FROM_NAME,
        'timeout': int(Config.MAIL_TIMEOUT),
    }


def send_email(subject, html_body, recipient, *, config=None):
    """Envoie un email HTML via SMTP. Retourne un dict descriptif (jamais
    d'exception) : {'delivered': True} si envoye, '' delivered False'' si
    desactive / non configure / echec."""
    if not recipient:
        logger.warning('EMAIL: destinataire manquant, envoi ignore')
        return {'success': False, 'delivered': False, 'message': 'Destinataire manquant'}

    if not getattr(Config, 'MAIL_ENABLED', False):
        logger.info('EMAIL desactive (MAIL_ENABLED=false) : %s <- %s', recipient, subject)
        return {'success': True, 'delivered': False, 'message': 'SMTP desactive (MAIL_ENABLED=false)'}

    conf = _build_smtp_config(config)
    host = conf['host']
    if not host:
        logger.info('EMAIL: SMTP non configure (MAIL_HOST absent) pour %s', recipient)
        return {'success': True, 'delivered': False, 'message': 'SMTP non configure (MAIL_HOST)'}

    msg_from = formataddr((conf['from_name'], conf['from'])) if conf['from'] else 'erp@localhost'

    msg = MIMEMultipart('alternative')
    msg['From'] = msg_from
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP(host, conf['port'], timeout=conf['timeout']) as server:
            server.ehlo()
            if conf['use_tls']:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            if conf.get('user'):
                server.login(conf['user'], conf['password'] or '')
            server.send_message(msg)
        logger.info('EMAIL envoye : %s -> %s', subject, recipient)
        return {'success': True, 'delivered': True, 'recipient': recipient}
    except Exception as exc:
        logger.exception('Echec envoi email a %s', recipient)
        return {'success': False, 'delivered': False, 'message': str(exc), 'recipient': recipient}


def _tenant_label(tenant):
    if not tenant:
        return _APP_NAME
    nom = getattr(tenant, 'nom', None) or getattr(tenant, 'name', None)
    return str(nom).strip() or _APP_NAME


def _user_full_name(user):
    nom = getattr(user, 'nom', None)
    prenom = getattr(user, 'prenom', None)
    return ' '.join(x for x in (prenom, nom) if x).strip()


# ============================================================
# EMAILS METIER
# ============================================================

def send_welcome_email(user, tenant, temporary_password, *, app_url=None):
    email = getattr(user, 'email', '')
    if not email:
        return {'success': False, 'delivered': False, 'message': 'Email utilisateur manquant'}

    full = _user_full_name(user)
    tenant_label = html.escape(_tenant_label(tenant))
    identifiant = html.escape(email)
    temp_pwd = html.escape(str(temporary_password))

    subject = f'Bienvenue sur {_APP_NAME}'
    html_body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;color:#111111">'
        f'<h2 style="color:#111111">Bienvenue{(" " + html.escape(full)) if full else ""} !</h2>'
        f'<p>Un compte vient d&#39;être créé pour vous sur <strong>{tenant_label}</strong>.</p>'
        f'<p>Votre identifiant de connexion : <strong>{identifiant}</strong></p>'
        f'<p>Votre mot de passe temporaire : <strong>{temp_pwd}</strong></p>'
        '<p><em>Ce mot de passe est temporaire : vous devrez le changer dès votre première connexion.</em></p>'
        '<p style="color:#77776f;font-size:12px">Merci de ne pas répondre à cet email.</p>'
        '</div>'
    )
    return send_email(subject, html_body, email)


def send_password_reset_email(user, tenant, raw_token, *, expires_in_minutes=30, app_url=None):
    email = getattr(user, 'email', '')
    if not email or not raw_token:
        return {'success': False, 'delivered': False, 'message': 'Adresse ou token manquant'}

    base = (app_url or Config.FRONTEND_RESET_URL).rstrip('/')
    link = f"{base}/reset-password/{raw_token}"
    tenant_label = html.escape(_tenant_label(tenant))
    safe_link = html.escape(link)
    ttl = max(1, int(expires_in_minutes))

    subject = 'Réinitialisation de votre mot de passe'
    html_body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;color:#111111">'
        '<h2 style="color:#111111">Réinitialisation de mot de passe</h2>'
        f'<p>Vous avez demandé la réinitialisation de votre mot de passe sur <strong>{tenant_label}</strong>.</p>'
        f'<p>Ce lien est valable <strong>{ttl} minutes</strong>.</p>'
        f'<p style="margin:18px 0"><a href="{safe_link}" '
        'style="background:#d4af37;color:#111111;padding:10px 16px;text-decoration:none;'
        'border-radius:6px;font-weight:600">Réinitialiser mon mot de passe</a></p>'
        f'<p>Si le bouton ne fonctionne pas, copiez ce lien : <br/><code>{safe_link}</code></p>'
        '<p style="color:#77776f;font-size:12px">Si vous n&#39;êtes pas à l&#39;origine de cette demande, ignorez cet email.</p>'
        '</div>'
    )
    return send_email(subject, html_body, email)


def send_password_changed_email(user, tenant, *, changed_at=None, app_url=None):
    email = getattr(user, 'email', '')
    if not email:
        return {'success': False, 'delivered': False, 'message': 'Email utilisateur manquant'}

    full = _user_full_name(user)
    tenant_label = html.escape(_tenant_label(tenant))
    when = (changed_at or datetime.utcnow()).strftime('%d/%m/%Y %H:%M')

    subject = 'Votre mot de passe a été modifié'
    html_body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;color:#111111">'
        '<h2 style="color:#111111">Votre mot de passe a été modifié</h2>'
        f'<p>Bonjour{(" " + html.escape(full)) if full else ""},</p>'
        f'<p>Le mot de passe de votre compte <strong>{email}</strong> a été modifié le {when}.</p>'
        f'<p>Si vous n&#39;êtes pas à l&#39;origine de ce changement, contactez immédiatement l&#39;administrateur de {tenant_label}.</p>'
        '</div>'
    )
    return send_email(subject, html_body, email)


def send_invoice_email(invoice_id, recipient_email, smtp_config=None):
    if not recipient_email:
        return {'success': False, 'delivered': False, 'message': 'Destinataire manquant'}
    subject = f'Facture #{invoice_id}'
    html_body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;color:#111111">'
        f'<h2 style="color:#111111">Facture #{invoice_id}</h2>'
        '<p>Votre facture est disponible.</p>'
        '</div>'
    )
    return send_email(subject, html_body, recipient_email, config=smtp_config)


def send_payment_confirmation(payment_id, recipient_email, smtp_config=None):
    if not recipient_email:
        return {'success': False, 'delivered': False, 'message': 'Destinataire manquant'}
    subject = f'Confirmation de paiement #{payment_id}'
    html_body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;color:#111111">'
        f'<h2 style="color:#111111">Paiement confirmé</h2>'
        f'<p>Votre paiement #{payment_id} a été confirmé. Merci !</p>'
        '</div>'
    )
    return send_email(subject, html_body, recipient_email, config=smtp_config)


def send_stock_alert(product_id, threshold, recipient_email, smtp_config=None):
    if not recipient_email:
        return {'success': False, 'delivered': False, 'message': 'Destinataire manquant'}
    subject = f'Alerte stock produit #{product_id}'
    html_body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;color:#111111">'
        f'<h2 style="color:#111111">Alerte stock</h2>'
        f'<p>Le produit #{product_id} a atteint le seuil de <strong>{html.escape(str(threshold))}</strong>.</p>'
        '</div>'
    )
    return send_email(subject, html_body, recipient_email, config=smtp_config)