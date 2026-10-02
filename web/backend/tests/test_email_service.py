"""Tests du service email (email_service.py).

Couvre :
- envoi SMTP reel (mocke) avec MAIL_ENABLED
- gating MAIL_ENABLED=false
- gating MAIL_HOST absent
- destinataire manquant
- erreur SMTP graceful
- emails metier : bienvenue, reset, changed, facture, paiement, stock
- fusion de config SMTP custom
- utilisation TLS
"""

import os
import base64
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from unittest.mock import patch, MagicMock

import pytest

from app.config.settings import Config


def _decode_payload(msg):
    """Decode the first alternative payload from a MIME message.

    ``send_email`` builds a ``multipart/alternative`` message with an
    ``text/html`` part.  ``get_payload()`` may return it base64-encoded.
    """
    raw = msg.get_payload()[0].get_payload()
    try:
        return base64.b64decode(raw).decode('utf-8')
    except Exception:
        return raw


@pytest.fixture(autouse=True)
def _reset_mail_config():
    originals = {
        'MAIL_ENABLED': getattr(Config, 'MAIL_ENABLED', False),
        'MAIL_HOST': getattr(Config, 'MAIL_HOST', None),
        'MAIL_PORT': getattr(Config, 'MAIL_PORT', 587),
        'MAIL_USERNAME': getattr(Config, 'MAIL_USERNAME', None),
        'MAIL_PASSWORD': getattr(Config, 'MAIL_PASSWORD', None),
        'MAIL_USE_TLS': getattr(Config, 'MAIL_USE_TLS', True),
        'MAIL_FROM': getattr(Config, 'MAIL_FROM', None),
        'MAIL_FROM_NAME': getattr(Config, 'MAIL_FROM_NAME', 'MIHAJA ERP'),
        'MAIL_TIMEOUT': getattr(Config, 'MAIL_TIMEOUT', 30),
        'MAIL_PROVIDER': getattr(Config, 'MAIL_PROVIDER', 'smtp'),
        'BREVO_API_KEY': getattr(Config, 'BREVO_API_KEY', None),
        'BREVO_API_URL': getattr(Config, 'BREVO_API_URL', 'https://api.brevo.com/v3/smtp/email'),
        'BREVO_SENDER_EMAIL': getattr(Config, 'BREVO_SENDER_EMAIL', None),
        'BREVO_SENDER_NAME': getattr(Config, 'BREVO_SENDER_NAME', 'MIHAJA ERP'),
        'FRONTEND_RESET_URL': getattr(Config, 'FRONTEND_RESET_URL', 'http://localhost:3000'),
    }
    yield
    for k, v in originals.items():
        setattr(Config, k, v)


class _SmtpCapture:
    """Captire les emails envoyes via smtplib sans envoyer reellement."""

    def __init__(self):
        self.messages = []

    def __call__(self, host, port, timeout=30):
        self._host = host
        self._port = port
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def ehlo(self):
        pass

    def starttls(self, context=None):
        pass

    def login(self, user, password):
        pass

    def send_message(self, msg):
        self.messages.append(msg)


class TestSendEmailGating:

    def test_delivered_when_smtp_enabled(self):
        from app.services.email_service import send_email
        Config.MAIL_ENABLED = True
        Config.MAIL_HOST = 'smtp.test.mg'
        Config.MAIL_PORT = 587

        capture = _SmtpCapture()
        with patch('app.services.email_service.smtplib.SMTP', capture):
            result = send_email('Sujet', '<p>Body</p>', 'dest@test.mg')

        assert result['delivered'] is True
        assert result['success'] is True
        assert len(capture.messages) == 1

    def test_not_delivered_when_mail_disabled(self):
        from app.services.email_service import send_email
        Config.MAIL_ENABLED = False

        result = send_email('Sujet', '<p>Body</p>', 'dest@test.mg')
        assert result['delivered'] is False
        assert result['success'] is True

    def test_not_delivered_when_no_host(self):
        from app.services.email_service import send_email
        Config.MAIL_ENABLED = True
        Config.MAIL_HOST = None

        result = send_email('Sujet', '<p>Body</p>', 'dest@test.mg')
        assert result['delivered'] is False

    def test_no_recipient(self):
        from app.services.email_service import send_email
        Config.MAIL_ENABLED = True
        Config.MAIL_HOST = 'smtp.test.mg'

        result = send_email('Sujet', '<p>Body</p>', None)
        assert result['delivered'] is False
        assert result['success'] is False

    def test_smtp_error_returns_no_exception(self):
        from app.services.email_service import send_email
        Config.MAIL_ENABLED = True
        Config.MAIL_HOST = 'smtp.test.mg'
        Config.MAIL_PORT = 587

        class _FailingSmtp:
            def __call__(self, host, port, timeout=30):
                return self
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def ehlo(self):
                pass
            def starttls(self, context=None):
                pass
            def send_message(self, msg):
                raise smtplib.SMTPException('Connection refused')

        with patch('app.services.email_service.smtplib.SMTP', _FailingSmtp()):
            result = send_email('Sujet', '<p>Body</p>', 'dest@test.mg')

        assert result['delivered'] is False
        assert result['success'] is False
        assert 'Connection refused' in result['message']


class TestEmailContent:

    def test_welcome_email_content(self):
        from app.services.email_service import send_welcome_email
        Config.MAIL_ENABLED = True
        Config.MAIL_HOST = 'smtp.test.mg'

        user = MagicMock()
        user.email = 'newuser@test.mg'
        user.nom = 'Rakoto'
        user.prenom = 'Jean'

        tenant = MagicMock()
        tenant.nom = 'Entreprise Test'

        capture = _SmtpCapture()
        with patch('app.services.email_service.smtplib.SMTP', capture):
            result = send_welcome_email(user, tenant, 'TempPass123!')

        assert result['delivered'] is True
        assert len(capture.messages) == 1
        body = _decode_payload(capture.messages[0])
        assert 'TempPass123!' in body
        assert 'Bienvenue' in body
        assert 'Entreprise Test' in body

    def test_welcome_email_no_email_user(self):
        from app.services.email_service import send_welcome_email
        Config.MAIL_ENABLED = True

        user = MagicMock()
        user.email = None

        result = send_welcome_email(user, None, 'TempPass123!')
        assert result['delivered'] is False

    def test_password_reset_email_content(self):
        from app.services.email_service import send_password_reset_email
        Config.MAIL_ENABLED = True
        Config.MAIL_HOST = 'smtp.test.mg'
        Config.FRONTEND_RESET_URL = 'http://localhost:3000'

        user = MagicMock()
        user.email = 'user@test.mg'

        tenant = MagicMock()
        tenant.nom = 'Mon Tenant'

        capture = _SmtpCapture()
        with patch('app.services.email_service.smtplib.SMTP', capture):
            result = send_password_reset_email(user, tenant, 'raw-token-abc', expires_in_minutes=60)

        assert result['delivered'] is True
        body = _decode_payload(capture.messages[0])
        assert 'reset-password/raw-token-abc' in body
        assert '60 minutes' in body

    def test_password_reset_no_email(self):
        from app.services.email_service import send_password_reset_email
        Config.MAIL_ENABLED = True

        user = MagicMock()
        user.email = None

        result = send_password_reset_email(user, None, 'token')
        assert result['delivered'] is False

    def test_password_changed_email_content(self):
        from app.services.email_service import send_password_changed_email
        Config.MAIL_ENABLED = True
        Config.MAIL_HOST = 'smtp.test.mg'

        user = MagicMock()
        user.email = 'user@test.mg'
        user.nom = 'Rakoto'
        user.prenom = 'Jean'

        tenant = MagicMock()
        tenant.nom = 'Mon Tenant'

        capture = _SmtpCapture()
        with patch('app.services.email_service.smtplib.SMTP', capture):
            result = send_password_changed_email(user, tenant)

        assert result['delivered'] is True
        body = _decode_payload(capture.messages[0])
        assert 'modifi' in body.lower()

    def test_invoice_email_content(self):
        from app.services.email_service import send_invoice_email
        Config.MAIL_ENABLED = True
        Config.MAIL_HOST = 'smtp.test.mg'

        capture = _SmtpCapture()
        with patch('app.services.email_service.smtplib.SMTP', capture):
            result = send_invoice_email(42, 'client@test.mg')

        assert result['delivered'] is True
        body = _decode_payload(capture.messages[0])
        assert '#42' in body

    def test_payment_confirmation_content(self):
        from app.services.email_service import send_payment_confirmation
        Config.MAIL_ENABLED = True
        Config.MAIL_HOST = 'smtp.test.mg'

        capture = _SmtpCapture()
        with patch('app.services.email_service.smtplib.SMTP', capture):
            result = send_payment_confirmation(99, 'client@test.mg')

        assert result['delivered'] is True
        body = _decode_payload(capture.messages[0])
        assert '#99' in body

    def test_stock_alert_content(self):
        from app.services.email_service import send_stock_alert
        Config.MAIL_ENABLED = True
        Config.MAIL_HOST = 'smtp.test.mg'

        capture = _SmtpCapture()
        with patch('app.services.email_service.smtplib.SMTP', capture):
            result = send_stock_alert(7, 10, 'manager@test.mg')

        assert result['delivered'] is True
        body = _decode_payload(capture.messages[0])
        assert '#7' in body
        assert '10' in body

    def test_stock_alert_no_recipient(self):
        from app.services.email_service import send_stock_alert
        result = send_stock_alert(1, 10, None)
        assert result['delivered'] is False


class TestSmtpConfig:

    def test_build_smtp_config_with_override(self):
        from app.services.email_service import _build_smtp_config
        Config.MAIL_HOST = 'default.mg'
        Config.MAIL_PORT = 587

        config = _build_smtp_config({
            'host': 'custom.mg',
            'port': 465,
            'user': 'custom_user',
            'password': 'custom_pass',
        })

        assert config['host'] == 'custom.mg'
        assert config['port'] == 465
        assert config['user'] == 'custom_user'
        assert config['password'] == 'custom_pass'

    def test_build_smtp_config_default(self):
        from app.services.email_service import _build_smtp_config
        Config.MAIL_HOST = 'default.mg'
        Config.MAIL_PORT = 587
        Config.MAIL_USERNAME = 'default_user'

        config = _build_smtp_config()

        assert config['host'] == 'default.mg'
        assert config['port'] == 587
        assert config['user'] == 'default_user'

    def test_send_email_uses_tls(self):
        from app.services.email_service import send_email
        Config.MAIL_ENABLED = True
        Config.MAIL_HOST = 'smtp.test.mg'
        Config.MAIL_PORT = 587
        Config.MAIL_USE_TLS = True
        Config.MAIL_USERNAME = 'user'
        Config.MAIL_PASSWORD = 'pass'

        tls_called = []

        class _TlsCapture:
            def __call__(self, host, port, timeout=30):
                return self
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def ehlo(self):
                pass
            def starttls(self, context=None):
                tls_called.append(True)
            def login(self, user, password):
                pass
            def send_message(self, msg):
                pass

        with patch('app.services.email_service.smtplib.SMTP', _TlsCapture()):
            send_email('Sujet', '<p>Body</p>', 'dest@test.mg')

        assert len(tls_called) == 1


class _BrevoResponse:
    def __init__(self, status_code=201, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class TestBrevoProvider:

    @pytest.fixture(autouse=True)
    def _configure_brevo(self):
        Config.MAIL_ENABLED = True
        Config.MAIL_PROVIDER = 'brevo'
        Config.BREVO_API_KEY = 'brevo-test-secret'
        Config.BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'
        Config.BREVO_SENDER_EMAIL = 'sender@example.com'
        Config.BREVO_SENDER_NAME = 'MIHAJA ERP'
        Config.MAIL_TIMEOUT = 8

    def test_brevo_success_uses_https_api(self):
        from app.services.email_service import send_email

        with patch(
            'app.services.email_service.requests.post',
            return_value=_BrevoResponse(201, {'messageId': '<brevo-message-id>'}),
        ) as post:
            result = send_email(
                'Sujet',
                '<p>Body</p>',
                'dest@example.com',
                reply_to='support@example.com',
            )

        assert result['success'] is True
        assert result['delivered'] is True
        assert result['status_code'] == 201
        assert result['message_id'] == '<brevo-message-id>'
        args, kwargs = post.call_args
        assert args == ('https://api.brevo.com/v3/smtp/email',)
        assert kwargs['timeout'] == 8
        assert kwargs['headers']['api-key'] == 'brevo-test-secret'
        assert kwargs['json']['sender'] == {
            'name': 'MIHAJA ERP',
            'email': 'sender@example.com',
        }
        assert kwargs['json']['to'] == [{'email': 'dest@example.com'}]
        assert kwargs['json']['replyTo'] == {'email': 'support@example.com'}

    def test_brevo_http_error_is_not_reported_as_delivered(self):
        from app.services.email_service import send_email

        with patch(
            'app.services.email_service.requests.post',
            return_value=_BrevoResponse(401, {'code': 'unauthorized'}),
        ):
            result = send_email('Sujet', '<p>Body</p>', 'dest@example.com')

        assert result['success'] is False
        assert result['delivered'] is False
        assert result['status_code'] == 401
        assert result['error_type'] == 'provider_http'
        assert result['provider_code'] == 'unauthorized'
        assert result['message'] == 'Brevo HTTP 401'

    def test_brevo_timeout_is_bounded_and_safe(self, caplog):
        from app.services.email_service import send_email

        caplog.set_level('ERROR')
        with patch(
            'app.services.email_service.requests.post',
            side_effect=requests.Timeout('timeout'),
        ) as post:
            result = send_email('Sujet', '<p>Body</p>', 'dest@example.com')

        assert result['success'] is False
        assert result['delivered'] is False
        assert result['error_type'] == 'timeout'
        assert result['message'] == 'Brevo indisponible (timeout)'
        assert 'brevo-test-secret' not in caplog.text
        assert post.call_args.kwargs['timeout'] == 8

    def test_brevo_configuration_missing(self):
        from app.services.email_service import send_email

        Config.BREVO_API_KEY = None
        with patch('app.services.email_service.requests.post') as post:
            result = send_email('Sujet', '<p>Body</p>', 'dest@example.com')

        assert result['success'] is False
        assert result['delivered'] is False
        assert result['error_type'] == 'configuration'
        post.assert_not_called()

    def test_password_reset_email_uses_brevo_and_keeps_template(self):
        from app.services.email_service import send_password_reset_email

        user = MagicMock()
        user.email = 'user@example.com'
        tenant = MagicMock()
        tenant.nom = 'Mon Tenant'

        with patch(
            'app.services.email_service.requests.post',
            return_value=_BrevoResponse(201, {'messageId': '<reset-id>'}),
        ) as post:
            result = send_password_reset_email(
                user,
                tenant,
                'raw-token-abc',
                expires_in_minutes=60,
                app_url='https://example.com',
            )

        assert result['delivered'] is True
        payload = post.call_args.kwargs['json']
        assert 'reset-password/raw-token-abc' in payload['htmlContent']
        assert '60 minutes' in payload['htmlContent']
