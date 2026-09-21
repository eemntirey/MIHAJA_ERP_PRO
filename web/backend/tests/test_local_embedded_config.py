# web/backend/tests/test_local_embedded_config.py
# Mode backend embarque (desktop hors-ligne, FLASK_ENV=local-embedded) :
# SQLite local obligatoire + URL du serveur central de replication requise.
import pytest
from app import create_app


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    monkeypatch.setenv('FLASK_ENV', 'local-embedded')
    monkeypatch.setenv('LOCAL_DB_PATH', str(tmp_path / 'erp-local.db'))
    monkeypatch.setenv('REPLICATION_URL', 'https://erp.mihaja.mg')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    return tmp_path


def test_local_embedded_uses_sqlite_file(local_env):
    app = create_app()
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    assert uri.startswith('sqlite:///')
    assert 'erp-local.db' in uri
    assert app.config['FLASK_ENV'] == 'local-embedded'
    assert app.config['REPLICATION_URL'] == 'https://erp.mihaja.mg'
    assert app.config['REPLICATION_DEVICE_ID']


def test_local_embedded_requires_replication_url(monkeypatch, tmp_path):
    monkeypatch.setenv('FLASK_ENV', 'local-embedded')
    monkeypatch.setenv('LOCAL_DB_PATH', str(tmp_path / 'erp-local.db'))
    monkeypatch.delenv('REPLICATION_URL', raising=False)
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    with pytest.raises(ValueError, match='REPLICATION_URL'):
        create_app()


def test_local_embedded_requires_local_db_path(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'local-embedded')
    monkeypatch.delenv('LOCAL_DB_PATH', raising=False)
    monkeypatch.setenv('REPLICATION_URL', 'https://erp.mihaja.mg')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    with pytest.raises(ValueError, match='LOCAL_DB_PATH'):
        create_app()


def test_central_production_still_rejects_sqlite(monkeypatch):
    # Garde-fou : seul le backend embarque local utilise SQLite, jamais le
    # serveur central en production.
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///erp.db')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    with pytest.raises(ValueError):
        create_app()
