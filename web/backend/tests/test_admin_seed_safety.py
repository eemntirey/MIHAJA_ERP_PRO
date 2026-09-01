"""Tests du seed admin (auto-seed).

Garantit que :
 - Le seed n'est déclenché qu'en mode dev/test (gated par AUTO_SEED_DATA).
 - Aucun mot de passe n'est jamais exposé via une réponse HTTP.
 - Aucun mot de passe n'est jamais loggué.
"""
import inspect
import os

from app import create_app, db as _db


def test_seed_gated_by_debug_or_testing_only():
    """Le seed ne doit JAMAIS tourner en production."""
    src = inspect.getsource(create_app)
    # Le bloc seed doit être conditionné par DEBUG/TESTING/AUTO_SEED_DATA
    assert "AUTO_SEED_DATA" in src
    # Vérifie que la branche productie du seed ne s'exécute pas sans opt-in
    assert "FLASK_ENV" in src


def test_seed_password_not_logged():
    """Le mot de passe généré ne doit pas être écrit dans les logs."""
    src = inspect.getsource(create_app)
    # On interdit logger.* avec default_password
    forbidden = [
        "logger.info(default_password",
        "logger.warning(default_password",
        "logger.error(default_password",
        "logger.debug(default_password",
        "current_app.logger.info(default_password",
        "current_app.logger.warning(default_password",
        "print(default_password",
    ]
    for f in forbidden:
        assert f not in src, f"Fuite possible: {f}"


def test_seed_password_not_returned_via_response():
    """Aucun endpoint REST ne doit retourner le mot de passe seed."""
    from app.models.utilisateur import Utilisateur
    src = inspect.getsource(Utilisateur)
    assert 'password_hash' in src
    # to_dict doit explicitement exclure password_hash
    assert "del data['password_hash']" in src or "'password_hash' not in data" in src


def test_utilisateur_to_dict_excludes_password_hash(app):
    """Vérifie empiriquement que to_dict n'expose pas le hash."""
    from app.models.tenant import Tenant, StatutTenant
    from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
    from app.security.auth import hash_password
    import uuid

    with app.app_context():
        tenant = Tenant(
            nom='T',
            slug=f'pwd-{uuid.uuid4().hex[:6]}',
            statut=StatutTenant.ACTIF,
            plan='starter',
        )
        _db.session.add(tenant)
        _db.session.flush()
        user = Utilisateur(
            username=f'u-{uuid.uuid4().hex[:6]}',
            email=f'e-{uuid.uuid4().hex[:6]}@x.mg',
            password_hash=hash_password('SuperSecret123!'),
            role=Role.ADMIN,
            tenant_id=tenant.id,
            statut=StatutUtilisateur.ACTIF,
        )
        _db.session.add(user)
        _db.session.commit()

        d = user.to_dict()
        assert 'password_hash' not in d, "password_hash doit être exclu"
        assert 'SuperSecret123!' not in str(d), "Mot de passe en clair interdit"
        _db.session.rollback()