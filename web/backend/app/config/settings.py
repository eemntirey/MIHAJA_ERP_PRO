import os
import uuid
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required")
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # Database
    DEFAULT_DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'postgresql+psycopg://erp_user:erp_password@localhost:5432/erp_db'
    )
    SQLALCHEMY_DATABASE_URI = DEFAULT_DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {}

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY environment variable is required")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'

    # Celery / Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    # Email
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_HOST = os.getenv('MAIL_HOST') or MAIL_SERVER
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes', 'on')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    # Interrupteur global du service d'emails. Desactive par defaut : aucun
    # envoi SMTP sans opt-in explicite (MAIL_ENABLED=true) — protege les tests
    # et les environnements de dev contre les envois accidentels.
    MAIL_ENABLED = os.getenv('MAIL_ENABLED', 'false').lower() in ('1', 'true', 'yes', 'on')
    MAIL_FROM = os.getenv('MAIL_FROM', MAIL_USERNAME or 'no-reply@mihaja-erp.local')
    MAIL_FROM_NAME = os.getenv('MAIL_FROM_NAME', 'MIHAJA ERP')
    MAIL_CONTACT_RECIPIENT = os.getenv('MAIL_CONTACT_RECIPIENT') or MAIL_USERNAME
    MAIL_TIMEOUT = int(os.getenv('MAIL_TIMEOUT', '30'))

    # Securite / reset
    PASSWORD_RESET_TTL_MINUTES = int(os.getenv('PASSWORD_RESET_TTL_MINUTES', '30'))
    FRONTEND_RESET_URL = os.getenv('FRONTEND_RESET_URL', 'http://localhost:3000')

    # Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max

    # CORS - inclut le tunnel de développement HTTPS pour Socket.IO (dev only)
    # et Expo web de l'app mobile (port 8081).
    CORS_ORIGINS = os.getenv(
        'CORS_ORIGINS',
        'http://localhost:3000,http://127.0.0.1:3000,http://localhost:8081,'
        'http://127.0.0.1:8081,https://bj470sl0-3000.inc1.devtunnels.ms'
    ).split(',') if os.getenv('CORS_ORIGINS') else []

    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    # Multi-tenancy
    DEFAULT_TENANT_SLUG = 'default'
    DEFAULT_TENANT_DOMAIN = 'localhost'
    DEFAULT_TENANT_NAME = 'Tenant Par Défaut'

    # Currency & Localization (Madagascar)
    CURRENCY_CODE = 'MGA'
    CURRENCY_SYMBOL = 'Ar'
    CURRENCY_LOCALE = 'mg-MG'
    DEFAULT_COUNTRY = 'Madagascar'

    # Papi Payment Gateway
    PAPI_API_URL = os.getenv('PAPI_API_URL', 'https://app.papi.mg/dashboard/api/payment-links')
    PAPI_API_KEY = os.getenv('PAPI_API_KEY')
    PAPI_ENVIRONMENT = os.getenv('PAPI_ENVIRONMENT', 'sandbox')
    PAPI_WEBHOOK_SECRET = os.getenv('PAPI_WEBHOOK_SECRET')
    PAPI_CALLBACK_URL = os.getenv('PAPI_CALLBACK_URL')

    @classmethod
    def validate(cls):
        # L'URL est relue dans l'environnement a l'appel : les tests (et le
        # backend embarque) positionnent DATABASE_URL apres l'import du module.
        database_url = os.getenv('DATABASE_URL') or cls.DEFAULT_DATABASE_URL
        if os.getenv('FLASK_ENV', '').lower() == 'production' and database_url.startswith('sqlite'):
            raise ValueError(
                'Production environment requires PostgreSQL DATABASE_URL; SQLite is not allowed.'
            )

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class _EnvVar:
    """Descripteur lisant une variable d'environnement A L'ACCES.

    Les valeurs de `Config` sont figees a l'import (attributs de classe) ;
    pour le backend embarque, Electron (et les tests) positionnent
    LOCAL_DB_PATH / REPLICATION_URL apres l'import du module. Un descripteur
    evite donc de servir une valeur obsolete.
    """

    def __init__(self, name, default='', prefix=''):
        self.name = name
        self.default = default
        self.prefix = prefix

    def __get__(self, obj, objtype=None):
        return f"{self.prefix}{os.getenv(self.name, self.default)}"


class _DeviceIdVar:
    """Identifiant de poste : env var sinon UUID genere UNE seule fois."""

    def __get__(self, obj, objtype=None):
        global _LOCAL_DEVICE_ID
        if _LOCAL_DEVICE_ID is None:
            _LOCAL_DEVICE_ID = os.getenv('REPLICATION_DEVICE_ID') or str(uuid.uuid4())
        return _LOCAL_DEVICE_ID


_LOCAL_DEVICE_ID = None


class LocalEmbeddedConfig(Config):
    """Config du backend embarque dans Electron (mode hors-ligne complet).

    SQLite local obligatoire ; les donnees metier sont repliquees vers le
    serveur central (REPLICATION_URL) par app/services/replication.
    """
    FLASK_ENV = 'local-embedded'
    SQLALCHEMY_DATABASE_URI = _EnvVar('LOCAL_DB_PATH', prefix='sqlite:///')
    REPLICATION_URL = _EnvVar('REPLICATION_URL')
    REPLICATION_DEVICE_ID = _DeviceIdVar()
    CELERY_BROKER_URL = None
    ENABLE_SOCKETIO = False

    @classmethod
    def validate(cls):
        if not os.getenv('LOCAL_DB_PATH'):
            raise ValueError('LOCAL_DB_PATH est requis en mode local-embedded.')
        if not os.getenv('REPLICATION_URL'):
            raise ValueError(
                "REPLICATION_URL est requis en mode local-embedded "
                "(URL du serveur central pour la réplication)."
            )


def get_config_class(env=None):
    """Factory de configuration : FLASK_ENV -> classe de config.

    `local-embedded` est reserve au backend embarque du desktop : SQLite
    local + URL de replication obligatoires.
    """
    env = (env if env is not None else os.getenv('FLASK_ENV', '')).strip().lower()
    if env == 'local-embedded':
        return LocalEmbeddedConfig
    if env == 'production':
        return ProductionConfig
    if env == 'testing':
        return TestingConfig
    if os.getenv('DEBUG', 'false').lower() == 'true':
        return DevelopmentConfig
    return Config


# Factory branch
if os.getenv('FLASK_ENV', '').lower() == 'local-embedded':
    CURRENT_CONFIG = LocalEmbeddedConfig
else:
    CURRENT_CONFIG = Config
