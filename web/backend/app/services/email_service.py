# -*- coding: utf-8 -*-
# app/services/email_service.py
# Service d'envoi d'emails transactionnels pour les flux metier : bienvenue,
# reset de mot de passe, changement de mot de passe, facture, paiement, stock.
# Le provider est selectionne via MAIL_PROVIDER. Brevo utilise uniquement son
# API HTTPS ; SMTP reste disponible pour compatibilite explicite (MAIL_PROVIDER=smtp).

import html
import logging
import smtplib

import requests
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


def _build_brevo_config(config=None):
    """Construit la configuration Brevo sans jamais exposer la cle API."""
    if config:
        return {
            'api_key': config.get('api_key') or getattr(Config, 'BREVO_API_KEY', None),
            'api_url': config.get('api_url') or getattr(
                Config, 'BREVO_API_URL', 'https://api.brevo.com/v3/smtp/email'
            ),
            'from': config.get('from') or getattr(Config, 'BREVO_SENDER_EMAIL', None)
            or getattr(Config, 'MAIL_FROM', None),
            'from_name': config.get('from_name') or getattr(Config, 'BREVO_SENDER_NAME', None)
            or getattr(Config, 'MAIL_FROM_NAME', _APP_NAME),
            'timeout': int(config.get('timeout') or getattr(Config, 'MAIL_TIMEOUT', 10)),
        }
    return {
        'api_key': getattr(Config, 'BREVO_API_KEY', None),
        'api_url': getattr(Config, 'BREVO_API_URL', 'https://api.brevo.com/v3/smtp/email'),
        'from': getattr(Config, 'BREVO_SENDER_EMAIL', None) or getattr(Config, 'MAIL_FROM', None),
        'from_name': getattr(Config, 'BREVO_SENDER_NAME', None)
        or getattr(Config, 'MAIL_FROM_NAME', _APP_NAME),
        'timeout': int(getattr(Config, 'MAIL_TIMEOUT', 10)),
    }


def _send_smtp(subject, html_body, recipient, *, config=None, reply_to=None):
    """Transport SMTP historique, conserve uniquement pour compatibilite explicite."""
    conf = _build_smtp_config(config)
    if not conf['host']:
        logger.warning('EMAIL provider=smtp error_type=configuration')
        return {
            'success': False,
            'delivered': False,
            'message': 'SMTP non configure (MAIL_HOST)',
            'error_type': 'configuration',
        }

    msg_from = formataddr((conf['from_name'], conf['from'])) if conf['from'] else 'erp@localhost'
    msg = MIMEMultipart('alternative')
    msg['From'] = msg_from
    msg['To'] = recipient
    msg['Subject'] = subject
    if reply_to:
        msg['Reply-To'] = reply_to.replace('\r', ' ').replace('\n', ' ')
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP(host=conf['host'], port=conf['port'], timeout=conf['timeout']) as server:
            server.ehlo()
            if conf['use_tls']:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            if conf.get('user'):
                server.login(conf['user'], conf['password'] or '')
            server.send_message(msg)
        logger.info('EMAIL provider=smtp status=sent')
        return {'success': True, 'delivered': True, 'recipient': recipient}
    except Exception as exc:
        logger.error('EMAIL provider=smtp error_type=%s', type(exc).__name__)
        return {
            'success': False,
            'delivered': False,
            'message': str(exc),
            'error_type': type(exc).__name__,
            'recipient': recipient,
        }


def _send_brevo(subject, html_body, recipient, *, config=None, reply_to=None):
    """Envoie un email via l'API transactionnelle HTTPS Brevo."""
    conf = _build_brevo_config(config)
    if not conf['api_key'] or not conf['from']:
        logger.warning('EMAIL provider=brevo error_type=configuration')
        return {
            'success': False,
            'delivered': False,
            'message': 'Brevo non configure (BREVO_API_KEY/BREVO_SENDER_EMAIL)',
            'error_type': 'configuration',
        }

    payload = {
        'sender': {'name': conf['from_name'], 'email': conf['from']},
        'to': [{'email': recipient}],
        'subject': subject,
        'htmlContent': html_body,
    }
    if reply_to:
        safe_reply_to = reply_to.replace('\r', ' ').replace('\n', ' ').strip()
        if safe_reply_to:
            payload['replyTo'] = {'email': safe_reply_to}

    headers = {
        'api-key': conf['api_key'],
        'accept': 'application/json',
        'content-type': 'application/json',
    }

    try:
        response = requests.post(
            conf['api_url'],
            headers=headers,
            json=payload,
            timeout=conf['timeout'],
        )
        status_code = int(response.status_code)
        if 200 <= status_code < 300:
            try:
                data = response.json()
            except ValueError:
                data = {}
            result = {
                'success': True,
                'delivered': True,
                'recipient': recipient,
                'status_code': status_code,
            }
            if isinstance(data, dict) and data.get('messageId'):
                result['message_id'] = data['messageId']
            logger.info('EMAIL provider=brevo status=%s', status_code)
            return result

        try:
            data = response.json()
        except ValueError:
            data = {}
        provider_code = data.get('code') if isinstance(data, dict) else None
        if not isinstance(provider_code, str) or len(provider_code) > 100:
            provider_code = None
        logger.error(
            'EMAIL provider=brevo status=%s error_type=provider_http code=%s',
            status_code,
            provider_code,
        )
        result = {
            'success': False,
            'delivered': False,
            'message': f'Brevo HTTP {status_code}',
            'status_code': status_code,
            'error_type': 'provider_http',
            'recipient': recipient,
        }
        if provider_code:
            result['provider_code'] = provider_code
        return result
    except requests.Timeout:
        logger.error('EMAIL provider=brevo error_type=timeout')
        return {
            'success': False,
            'delivered': False,
            'message': 'Brevo indisponible (timeout)',
            'error_type': 'timeout',
            'recipient': recipient,
        }
    except requests.RequestException as exc:
        logger.error('EMAIL provider=brevo error_type=%s', type(exc).__name__)
        return {
            'success': False,
            'delivered': False,
            'message': 'Brevo indisponible',
            'error_type': type(exc).__name__,
            'recipient': recipient,
        }
    except Exception as exc:
        logger.error('EMAIL provider=brevo error_type=%s', type(exc).__name__)
        return {
            'success': False,
            'delivered': False,
            'message': 'Erreur inattendue du provider Brevo',
            'error_type': type(exc).__name__,
            'recipient': recipient,
        }


def send_email(subject, html_body, recipient, *, config=None, reply_to=None):
    """Envoie un email transactionnel via le provider configure."""
    if not recipient:
        logger.warning('EMAIL error_type=missing_recipient')
        return {
            'success': False,
            'delivered': False,
            'message': 'Destinataire manquant',
            'error_type': 'missing_recipient',
        }

    if not getattr(Config, 'MAIL_ENABLED', False):
        logger.info('EMAIL disabled')
        return {
            'success': True,
            'delivered': False,
            'message': 'Service email desactive',
            'error_type': 'disabled',
        }

    provider = str(getattr(Config, 'MAIL_PROVIDER', 'smtp') or 'smtp').strip().lower()
    if provider == 'brevo':
        return _send_brevo(subject, html_body, recipient, config=config, reply_to=reply_to)
    if provider == 'smtp':
        return _send_smtp(subject, html_body, recipient, config=config, reply_to=reply_to)

    logger.error('EMAIL provider=%s error_type=unsupported_provider', provider)
    return {
        'success': False,
        'delivered': False,
        'message': 'Provider email non supporte',
        'error_type': 'unsupported_provider',
        'provider': provider,
        'recipient': recipient,
    }

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