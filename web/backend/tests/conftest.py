
import pytest
from app import create_app, db as _db
from app.models.utilisateur import Role


@pytest.fixture(scope='session')
def _db(app):
    """Alias session de la base de test."""
    return _db


@pytest.fixture(autouse=True)
def _db_isolation(app):
    """Isole chaque test via un SAVEPOINT PostgreSQL."""
    with app.app_context():
        conn = _db.engine.connect()
        trans = conn.begin()
        sess = _db.session
        nested = sess.begin_nested()
        yield
        try:
            sess.rollback()
        finally:
            try:
                nested.rollback()
            except Exception:
                pass
            try:
                trans.rollback()
            except Exception:
                pass
            conn.close()


@pytest.fixture(scope='session')
def app():
    import os
    os.environ['DATABASE_URL'] = 'postgresql+psycopg://postgres:eemntirey@localhost:55432/erp_test'
    os.environ['PAPI_API_URL'] = 'https://test.papi.mg/dashboard/api/payment-links'
    os.environ['PAPI_API_KEY'] = 'test-api-key'
    os.environ['PAPI_ENVIRONMENT'] = 'sandbox'
    os.environ['PAPI_CALLBACK_URL'] = 'http://localhost:5000/api/v1/papi/webhook'

    app = create_app()
    app.config['TESTING'] = True

    with app.app_context():
        from app.models.role_permission import RoleModel, Permission
        _db.drop_all()
        _db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
        _db.session.rollback()
