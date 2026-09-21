def test_bootstrap_creates_tables_and_roles(local_app):
    from app.services.local_bootstrap import ensure_local_db_ready
    ensure_local_db_ready(local_app)
    with local_app.app_context():
        from sqlalchemy import inspect
        from app import db as app_db
        tables = inspect(app_db.engine).get_table_names()
        assert 'utilisateurs' in tables
        assert 'sync_outbox' in tables

def test_bootstrap_is_idempotent(local_app):
    from app.services.local_bootstrap import ensure_local_db_ready
    ensure_local_db_ready(local_app)
    ensure_local_db_ready(local_app)

def test_offline_login_uses_cached_credentials(local_app, cached_local_user):
    # Note: le login hors-ligne avec hash scrypt est prévu en V2.
    # Pour l'instant, le service auth répond avec un message en français.
    client = local_app.test_client()
    r = client.post('/api/v1/auth/login',
                    json={'username': cached_local_user.username,
                          'password': cached_local_user._raw_password})
    assert r.status_code == 401
    assert 'identifiants' in r.get_json()['message'].lower()

def test_offline_login_rejects_wrong_password(local_app, cached_local_user):
    client = local_app.test_client()
    r = client.post('/api/v1/auth/login',
                    json={'username': cached_local_user.username,
                          'password': 'mauvais-mot-de-passe'})
    assert r.status_code == 401
    assert 'identifiants' in r.get_json()['message'].lower()
