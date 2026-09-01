
import pytest
from app import create_app, db as _db


@pytest.fixture(scope='session')
def app():
    import os
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['PAPI_API_URL'] = 'https://test.papi.mg/dashboard/api/payment-links'
    os.environ['PAPI_API_KEY'] = 'test-api-key'
    os.environ['PAPI_ENVIRONMENT'] = 'sandbox'
    os.environ['PAPI_CALLBACK_URL'] = 'http://localhost:5000/api/v1/papi/webhook'

    app = create_app()
    app.config['TESTING'] = True

    with app.app_context():
        from app.models.role_permission import RoleModel, Permission
        from app.models.utilisateur import Role
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
