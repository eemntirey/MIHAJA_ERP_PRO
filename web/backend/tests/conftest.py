
import pytest
from app import create_app, db as app_db
from app.models.utilisateur import Role
from tests._db_utils import reset_schema as _reset_schema


@pytest.fixture(scope='session')
def _db(app):
    """Alias session de la base de test."""
    return app_db


@pytest.fixture(autouse=True)
def _db_isolation(app):
    """Isole chaque test via un SAVEPOINT PostgreSQL."""
    with app.app_context():
        conn = app_db.engine.connect()
        trans = conn.begin()
        sess = app_db.session
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
        _reset_schema(app_db)
        app_db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        yield app
        _reset_schema(app_db)


@pytest.fixture(autouse=True, scope='session')
def _patch_db_drop_all():
    """Redirige ``db.drop_all`` vers ``reset_schema`` pour tous les tests.

    SQLAlchemy ne peut pas résoudre les cycles de ForeignKey dans le schéma
    de production (``tenants`` <-> ``utilisateurs``, ``livreurs`` <->
    ``vehicules``, ``utilisateurs`` <-> ``roles``, plus les auto-références
    ``utilisateurs.created_by``/``updated_by``). Beaucoup de fichiers de
    tests appellent ``db.drop_all()`` directement ; on remplace la méthode
    au niveau de la classe pour que le patch s'applique à toutes les
    instances et survive aux fixtures ``app`` redéfinies localement.
    """
    from flask_sqlalchemy import SQLAlchemy
    original = SQLAlchemy.drop_all

    def _patched_drop_all(self, *args, **kwargs):
        _reset_schema(self)
        return None

    SQLAlchemy.drop_all = _patched_drop_all
    try:
        yield
    finally:
        SQLAlchemy.drop_all = original


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield app_db
        app_db.session.rollback()
