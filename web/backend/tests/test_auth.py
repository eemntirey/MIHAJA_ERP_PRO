from unittest.mock import patch

import pytest

from app import create_app


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
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
        'message': 'Le service d’authentification n’a pas généré une session valide'
    }
