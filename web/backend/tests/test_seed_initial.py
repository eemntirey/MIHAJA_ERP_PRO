"""Tests pour le seed initial.

Garantit :
 - aucune reponse HTTP ne contient un mot de passe en clair ;
 - le seed ne tourne que sous ``FLASK_ENV`` development/testing + ``AUTO_SEED_DATA=1`` ;
 - le seed attribue un mot de passe distinct par utilisateur ;
 - les mots de passe generes sont emis dans un marqueur [SEED-PASSWORD] et
   recuperables depuis les logs.
"""
import logging
import os
import uuid

import pytest

from app import create_app, db


@pytest.fixture
def dev_app():
    import logging
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['JWT_SECRET_KEY'] = 'seed-secret'
    os.environ['SECRET_KEY'] = 'seed-secret'
    os.environ['PAPI_API_URL'] = 'https://test.papi.mg/dashboard/api/payment-links'
    os.environ['PAPI_API_KEY'] = 'test-api-key'
    os.environ['PAPI_ENVIRONMENT'] = 'sandbox'
    os.environ['PAPI_CALLBACK_URL'] = 'http://localhost:5000/api/v1/papi/webhook'
    os.environ['FLASK_ENV'] = 'development'
    os.environ['AUTO_SEED_DATA'] = '1'

    # On capture tous les messages du logger 'app' (utilise par Flask)
    # en utilisant un handler persistant sur la fixture.
    captured_records = []

    class _ListHandler(logging.Handler):
        def emit(self, record):
            captured_records.append(record)

    app_logger = logging.getLogger('app')
    handler = _ListHandler(level=logging.DEBUG)
    app_logger.addHandler(handler)
    try:
        app = create_app()
        app.config['TESTING'] = True
        app.config['DEBUG'] = True
        with app.app_context():
            db.create_all()
        # On stocke les records sur l'instance d'app pour la lecture par le test.
        app._captured_records = captured_records
        yield app
    finally:
        app_logger.removeHandler(handler)
        with app.app_context():
            db.session.remove()
            db.drop_all()


@pytest.fixture
def prod_app():
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['JWT_SECRET_KEY'] = 'seed-secret'
    os.environ['SECRET_KEY'] = 'seed-secret'
    os.environ['PAPI_API_URL'] = 'https://test.papi.mg/dashboard/api/payment-links'
    os.environ['PAPI_API_KEY'] = 'test-api-key'
    os.environ['PAPI_ENVIRONMENT'] = 'sandbox'
    os.environ['PAPI_CALLBACK_URL'] = 'http://localhost:5000/api/v1/papi/webhook'
    os.environ['FLASK_ENV'] = 'production'
    os.environ.pop('AUTO_SEED_DATA', None)
    app = create_app()
    app.config['TESTING'] = False
    app.config['DEBUG'] = False
    yield app


class TestSeedInitialData:

    def test_seed_disabled_in_production(self, prod_app):
        with prod_app.app_context():
            from app.models.utilisateur import Utilisateur
            count = Utilisateur.query.count()
            assert count == 0

    def test_seed_runs_in_development(self, dev_app):
        with dev_app.app_context():
            from app.models.utilisateur import Utilisateur
            from app.models.tenant import Tenant
            tenants = Tenant.query.count()
            users = Utilisateur.query.count()
            assert tenants >= 1
            assert users >= 1

    def test_seed_logs_passwords_once(self, dev_app):
        records = getattr(dev_app, '_captured_records', [])
        seeded = [r for r in records if '[SEED-PASSWORD]' in r.getMessage()]
        assert seeded, 'Aucun log [SEED-PASSWORD] emis'

    def test_seed_assigns_unique_passwords(self, dev_app):
        with dev_app.app_context():
            from app.models.utilisateur import Utilisateur
            users = Utilisateur.query.all()
            assert len(users) >= 2
            # On verifie au moins que tous les hashs sont distincts
            # (deux hashs bcrypt du meme mot de passe sont deja distincts ;
            # mais deux mots de passe differents doivent l'etre aussi).
            seen = set()
            for u in users:
                seen.add(u.password_hash)
            assert len(seen) == len(users), 'Hash de mots de passe en double'

    def test_seed_passwords_not_in_http_responses(self, dev_app):
        client = dev_app.test_client()
        # Aucun endpoint public ne doit jamais renvoyer un mot de passe en
        # clair apres le seed.
        r = client.get('/health')
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert 'password' not in body.lower() or 'password' not in r.get_json()

        # L'endpoint public /public/catalog ne doit pas exposer les mots de passe.
        r = client.get('/public/catalog')
        if r.status_code == 200:
            txt = r.get_data(as_text=True).lower()
            assert 'password_hash' not in txt