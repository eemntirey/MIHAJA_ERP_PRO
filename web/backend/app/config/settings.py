import os
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
    if os.getenv('FLASK_ENV', '').lower() == 'production' and DEFAULT_DATABASE_URL.startswith('sqlite'):
        raise ValueError(
            'Production environment requires PostgreSQL DATABASE_URL; SQLite is not allowed.'
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
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

    # Email service (Nouveaux alias pour app.services.email_service)
    MAIL_HOST = os.getenv('MAIL_HOST') or MAIL_SERVER
    MAIL_USERNAME_ALT = os.getenv('MAIL_USERNAME')  # alias
    MAIL_PASSWORD_ALT = os.getenv('MAIL_PASSWORD')  # alias
    MAIL_USE_TLS_ALT = os.getenv('MAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes', 'on')
    MAIL_FROM = os.getenv('MAIL_FROM', MAIL_USERNAME)
    MAIL_FROM_NAME = os.getenv('MAIL_FROM_NAME', 'MIHAJA ERP')
    MAIL_TIMEOUT = int(os.getenv('MAIL_TIMEOUT', '30'))

    # Securite / reset
    PASSWORD_RESET_TTL_MINUTES = int(os.getenv('PASSWORD_RESET_TTL_MINUTES', '30'))
    FRONTEND_RESET_URL = os.getenv('FRONTEND_RESET_URL', 'http://localhost:3000')

    # Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

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

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
