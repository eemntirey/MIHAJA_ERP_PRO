import os
from unittest.mock import patch

import pytest

from app import create_app


@pytest.fixture
def app(monkeypatch):
    # URL de test dérivée de l'environnement (jamais de credential en dur).
    _base = os.getenv('TEST_DATABASE_URL') or os.getenv('DATABASE_URL') or \
        'postgresql+psycopg://postgres@localhost:55432/erp_test'
    monkeypatch.setenv('DATABASE_URL', _base.rsplit('/', 1)[0] + '/erp_test')
    app = create_app()
    app.config.update(TESTING=True)
    return app


def test_login_returns_session_tokens(app):
    auth_result = {
        'access_token': 'access-token',
        'refresh_token': 'refresh-token',
        'user': {'id': 1, 'email': 'admin@example.com'},
        'tenant': {'id': 1, 'slug': 'demo'},
    }

    with patch('app.api.v1.auth.authenticate_user', return_value=(auth_result, None)):
        response = app.test_client().post(
            '/api/v1/auth/login',
            json={'username': 'admin@example.com', 'password': 'secret123'},
        )

    assert response.status_code == 200
    assert response.get_json() == auth_result


def test_login_rejects_incomplete_session_response(app):
    with patch(
        'app.api.v1.auth.authenticate_user',
        return_value=({'user': {'id': 1}}, None),
    ):
        response = app.test_client().post(
            '/api/v1/auth/login',
            json={'username': 'admin@example.com', 'password': 'secret123'},
        )

    assert response.status_code == 500
    assert response.get_json() == {
        'message': 'Le service d\u2019authentification n\u2019a pas g\u00e9n\u00e9r\u00e9 une session valide'
    }


# --- Régression : un token invalide ne doit JAMAIS produire de 500 ---
# flask_jwt_extended 4.x laisse fuiter des exceptions PyJWT brutes
# (DecodeError sur header non décodable, InvalidSignatureError...) : elles
# doivent être re-levees par le handler global (app/__init__.py) et retomber
# sur les loaders flask-jwt-extended -> 401 propre.

@pytest.mark.parametrize('authorization', [
    'Bearer garbage.token.here',                       # header non décodable
    'Bearer not-a-jwt',                                # pas un JWT du tout
    'Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.badbadbad',  # signature invalide
])
def test_refresh_invalid_token_returns_401(app, authorization):
    response = app.test_client().post(
        '/api/v1/auth/refresh',
        headers={'Authorization': authorization},
    )

    assert response.status_code == 401
    body = response.get_json()
    assert isinstance(body, dict)
    assert 'message' in body


def test_refresh_missing_header_returns_401(app):
    response = app.test_client().post('/api/v1/auth/refresh')

    assert response.status_code == 401
    assert response.get_json() == {
        'message': 'En-t\u00eate Authorization manquant ou invalide'
    }
