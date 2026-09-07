# -*- coding: utf-8 -*-
# app/services/email_service.py
"""Centralised email service for MIHAJA ERP."""

from __future__ import annotations
import logging, os, smtplib, ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)
DEFAULT_FROM = 'no-reply@mihaja-erp.local'
DEFAULT_FROM_NAME = 'MIHAJA ERP'
DEFAULT_TIMEOUT = 15


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'templates', 'emails',
)
import locale as _locale

_DEFAULT_ENCODING = 'utf-8'
try:
    _locale_encoding = _locale.getpreferredencoding(False) or 'utf-8'
    # Test rapide : le template doit etre lisible avec cet encodage
    with open(os.path.join(_TEMPLATES_DIR, 'welcome_account.html'), 'rb') as _f:
        _f.read().decode(_locale_encoding)
    _DEFAULT_ENCODING = _locale_encoding
except Exception:
    pass

_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR, encoding=_DEFAULT_ENCODING),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True, lstrip_blocks=True,
)


def get_email_config():
    host = os.getenv('MAIL_HOST', '').strip() or None
    port = int(os.getenv('MAIL_PORT', '587'))
    user = os.getenv('MAIL_USERNAME') or os.getenv('MAIL_USER') or None
    password = os.getenv('MAIL_PASSWORD') or None
    use_tls = _bool(os.getenv('MAIL_USE_TLS'), default=(port == 587))
    from_addr = os.getenv('MAIL_FROM') or user or DEFAULT_FROM
    from_name = os.getenv('MAIL_FROM_NAME', DEFAULT_FROM_NAME)
    timeout = int(os.getenv('MAIL_TIMEOUT', str(DEFAULT_TIMEOUT)))
    app_url = (
        os.getenv('APP_URL')
        or os.getenv('PUBLIC_APP_URL')
        or os.getenv('FRONTEND_URL')
        or 'http://localhost:3000'
    )
    return {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'use_tls': use_tls,
        'from_addr': from_addr,
        'from_name': from_name,
        'timeout': timeout,
        'app_url': app_url.rstrip('/'),
    }


def _render(template_name, context):
    return _env.get_template(template_name).render(**context)


def _build_message(subject, html_body, to_addr, from_name, from_addr):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f'{from_name} <{from_addr}>' if from_name else from_addr
    msg['To'] = to_addr
    msg.attach(MIMEText('MIHAJA ERP\n\n' + subject + '\n\n' + html_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    return msg


def send_email(subject, html_body, recipient, *, config=None):
    cfg = config or get_email_config()
    host = cfg.get('host')
    from_addr = cfg.get('from_addr') or DEFAULT_FROM
    from_name = cfg.get('from_name') or DEFAULT_FROM_NAME
    if not recipient:
        return {'success': False, 'recipient': None, 'error': 'no_recipient'}
    if not host:
        logger.info(
            '[EMAIL][DEV] Aucun MAIL_HOST defini : e-mail non envoye. To=%s Subject=%s',
            recipient, subject,
        )
        return {'success': True, 'recipient': recipient, 'delivered': False}
    try:
        msg = _build_message(subject, html_body, recipient, from_name, from_addr)
        with smtplib.SMTP(host, cfg.get('port', 587), timeout=cfg.get('timeout', DEFAULT_TIMEOUT)) as server:
            server.ehlo()
            if cfg.get('use_tls'):
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
            user_creds = cfg.get('user')
            if user_creds:
                server.login(user_creds, cfg.get('password') or '')
            server.send_message(msg)
        return {'success': True, 'recipient': recipient, 'delivered': True}
    except Exception as exc:
        logger.exception("Echec de l'envoi de l'e-mail a %s", recipient)
        return {'success': False, 'recipient': recipient, 'error': str(exc)}


def _user_full_name(user):
    parts = [getattr(user, 'prenom', None), getattr(user, 'nom', None)]
    return ' '.join(p for p in parts if p).strip() or getattr(user, 'username', '') or getattr(user, 'email', '')


def _tenant_name(tenant):
    if tenant is None:
        return 'MIHAJA ERP'
    return getattr(tenant, 'nom', None) or getattr(tenant, 'slug', None) or 'MIHAJA ERP'


def send_welcome_email(user, tenant, temporary_password, *, app_url=None):
    cfg = get_email_config()
    base_url = (app_url or cfg.get('app_url') or '').rstrip('/')
    context = {
        'user_full_name': _user_full_name(user),
        'user_email': getattr(user, 'email', ''),
        'tenant_name': _tenant_name(tenant),
        'temporary_password': temporary_password,
        'app_url': base_url,
    }
    html = _render('welcome_account.html', context)
    subject = 'Bienvenue sur MIHAJA ERP - Votre compte sur ' + context['tenant_name']
    return send_email(subject, html, context['user_email'])


def send_password_reset_email(user, tenant, raw_token, *, expires_in_minutes=30, app_url=None):
    cfg = get_email_config()
    base_url = (app_url or cfg.get('app_url') or '').rstrip('/')
    reset_link = base_url + '/reset-password/' + raw_token
    context = {
        'user_full_name': _user_full_name(user),
        'tenant_name': _tenant_name(tenant),
        'reset_link': reset_link,
        'expires_in_minutes': int(expires_in_minutes),
        'app_url': base_url,
    }
    html = _render('password_reset.html', context)
    subject = 'Reinitialisation de votre mot de passe MIHAJA ERP'
    return send_email(subject, html, getattr(user, 'email', ''))


def send_password_changed_email(user, tenant, *, changed_at=None, app_url=None):
    cfg = get_email_config()
    base_url = (app_url or cfg.get('app_url') or '').rstrip('/')
    when = changed_at or datetime.utcnow()
    context = {
        'user_full_name': _user_full_name(user),
        'tenant_name': _tenant_name(tenant),
        'changed_at': when.strftime('%d/%m/%Y a %H:%M UTC'),
        'app_url': base_url,
    }
    html = _render('password_changed.html', context)
    subject = 'Votre mot de passe MIHAJA ERP a ete modifie'
    return send_email(subject, html, getattr(user, 'email', ''))
