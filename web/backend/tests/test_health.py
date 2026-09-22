"""Tests minimalistes de santé de l'API (checklist CI de mise en production).

Couvre les smoke tests `GET /health` et `GET /ready` documentés dans
`docs/technical/CARTE_MISE_EN_PRODUCTION.md` (§5).
"""
from sqlalchemy import text


def test_health_ok(client):
    response = client.get('/health')
    assert response.status_code == 200
    body = response.get_json()
    assert body['status'] == 'healthy'
    assert body['service'] == 'erp-backend'
    assert body['checks']['database'] == 'connected'


def test_ready_ok(client):
    response = client.get('/ready')
    assert response.status_code == 200
    assert response.get_json() == {'ready': True}


def test_monitor_endpoint(client):
    response = client.get('/monitor')
    assert response.status_code == 200
    body = response.get_json()
    assert body['status'] == 'running'
    assert body['monitor'] is True


def test_schema_requis_present(client):
    """Les 4 tables critiques du diagnostic `REQUIRED_TABLES` existent."""
    from app import db

    with client.application.app_context():
        from sqlalchemy import inspect

        existing = set(inspect(db.engine).get_table_names())
    for table in ('tenants', 'utilisateurs', 'roles', 'permissions'):
        assert table in existing


def test_select_1_hors_http(db):
    """La base de test répond aux requêtes SQL simples (sans requête HTTP)."""
    with db.engine.connect() as conn:
        assert conn.execute(text('SELECT 1')).scalar() == 1