from tests._db_utils import test_database_url
import pytest


def test_local_embedded_config_uses_sqlite_file(monkeypatch, tmp_path):
    # Pas d'importlib.reload : LocalEmbeddedConfig lit l'environnement Ã 
    # l'ACCES (descripteurs _EnvVar / _DeviceIdVar) et validate() lit
    # os.getenv Ã  l'appel. Le module est dÃ©jÃ  importÃ© par conftest.
    monkeypatch.setenv('FLASK_ENV', 'local-embedded')
    monkeypatch.setenv('LOCAL_DB_PATH', str(tmp_path / 'erp-local.db'))
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('REPLICATION_URL', 'https://erp.mihaja.mg')
    from app.config.settings import LocalEmbeddedConfig
    assert LocalEmbeddedConfig.SQLALCHEMY_DATABASE_URI.startswith('sqlite:///')
    assert 'erp-local.db' in LocalEmbeddedConfig.SQLALCHEMY_DATABASE_URI
    assert LocalEmbeddedConfig.REPLICATION_URL == 'https://erp.mihaja.mg'
    assert LocalEmbeddedConfig.REPLICATION_DEVICE_ID


def test_local_embedded_requires_replication_url(monkeypatch, tmp_path):
    monkeypatch.setenv('FLASK_ENV', 'local-embedded')
    monkeypatch.setenv('LOCAL_DB_PATH', str(tmp_path / 'erp-local.db'))
    monkeypatch.delenv('REPLICATION_URL', raising=False)
    from app.config.settings import LocalEmbeddedConfig
    with pytest.raises(ValueError, match='REPLICATION_URL'):
        LocalEmbeddedConfig.validate()


def test_local_embedded_requires_local_db_path(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'local-embedded')
    monkeypatch.setenv('REPLICATION_URL', 'https://erp.mihaja.mg')
    monkeypatch.delenv('LOCAL_DB_PATH', raising=False)
    from app.config.settings import LocalEmbeddedConfig
    with pytest.raises(ValueError, match='LOCAL_DB_PATH'):
        LocalEmbeddedConfig.validate()


def test_central_production_still_rejects_sqlite(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///erp.db')
    from app.config.settings import Config
    with pytest.raises(ValueError):
        Config.validate()


def test_central_production_accepts_postgres(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('DATABASE_URL', test_database_url())
    from app.config.settings import Config
    # Aucune exception : PostgreSQL est acceptÃ© en production.
    Config.validate()