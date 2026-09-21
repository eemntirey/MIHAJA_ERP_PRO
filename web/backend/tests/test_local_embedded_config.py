import importlib
import pytest


def test_local_embedded_config_uses_sqlite_file(monkeypatch, tmp_path):
    monkeypatch.setenv('FLASK_ENV', 'local-embedded')
    monkeypatch.setenv('LOCAL_DB_PATH', str(tmp_path / 'erp-local.db'))
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('REPLICATION_URL', 'https://erp.mihaja.mg')
    import app.config.settings
    importlib.reload(app.config.settings)
    from app.config.settings import LocalEmbeddedConfig
    assert LocalEmbeddedConfig.SQLALCHEMY_DATABASE_URI.startswith('sqlite:///')
    assert 'erp-local.db' in LocalEmbeddedConfig.SQLALCHEMY_DATABASE_URI
    assert LocalEmbeddedConfig.REPLICATION_URL == 'https://erp.mihaja.mg'
    assert LocalEmbeddedConfig.REPLICATION_DEVICE_ID


def test_local_embedded_requires_replication_url(monkeypatch, tmp_path):
    monkeypatch.setenv('FLASK_ENV', 'local-embedded')
    monkeypatch.setenv('LOCAL_DB_PATH', str(tmp_path / 'erp-local.db'))
    monkeypatch.delenv('REPLICATION_URL', raising=False)
    import app.config.settings
    importlib.reload(app.config.settings)
    from app.config.settings import LocalEmbeddedConfig
    with pytest.raises(ValueError, match='REPLICATION_URL'):
        LocalEmbeddedConfig.validate()


def test_central_production_still_rejects_sqlite(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///erp.db')
    import app.config.settings
    importlib.reload(app.config.settings)
    from app.config.settings import Config
    with pytest.raises(ValueError):
        Config.validate()
