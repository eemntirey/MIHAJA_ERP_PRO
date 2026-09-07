"""Tests du module websockets/socket_events.

Vérifie qu'aucun import dynamique de modèle/framework n'est utilisé
dans les handlers (les imports doivent être explicites au top du module),
et que la logique JWT + tenant est conservée.
"""
import inspect
import os


def test_no_dynamic_imports_in_handlers():
    """Aucun handler WebSocket ne doit utiliser __import__ ni importer
    dynamiquement des modèles. Tous les imports doivent être au top du
    module (lisibilité, audit statique, performance).
    """
    import app.websockets.socket_events as mod

    src = inspect.getsource(mod)
    assert '__import__' not in src, (
        "socket_events.py utilise __import__ dynamiquement "
        "(risque d'import caché non audité)"
    )


def test_required_top_imports_present():
    """Les dépendances nécessaires doivent être importées explicitement."""
    import app.websockets.socket_events as mod

    assert hasattr(mod, 'decode_token'), "decode_token manquant"
    assert hasattr(mod, 'request'), "flask.request manquant"
    assert hasattr(mod, 'Utilisateur'), "Utilisateur manquant"
    assert hasattr(mod, 'is_super_admin'), "is_super_admin manquant"
    assert hasattr(mod, 'db'), "db (SQLAlchemy) manquant"


def test_register_handlers_returns_module():
    """Le module expose register_handlers et init_socketio."""
    import app.websockets.socket_events as mod

    assert callable(mod.register_handlers)
    assert callable(mod.init_socketio)
    assert callable(mod.broadcast_to_tenant)
    assert callable(mod.broadcast_to_user)


def test_tenant_belongs_to_user_returns_false_for_other_tenant(app):
    """Vérifie l'isolation multi-tenant: un user d'un autre tenant ne doit
    pas pouvoir s'abonner aux events d'un tenant différent.
    """
    from app import db
    from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
    from app.models.tenant import Tenant, StatutTenant
    from app.security.auth import hash_password
    import uuid

    with app.app_context():
        slug_a = f't-a-{uuid.uuid4().hex[:6]}'
        slug_b = f't-b-{uuid.uuid4().hex[:6]}'
        tenant_a = Tenant(nom='A', slug=slug_a, statut=StatutTenant.ACTIF, plan='starter')
        tenant_b = Tenant(nom='B', slug=slug_b, statut=StatutTenant.ACTIF, plan='starter')
        db.session.add_all([tenant_a, tenant_b])
        db.session.flush()

        user_a = Utilisateur(
            username=f'u-a-{uuid.uuid4().hex[:6]}',
            email=f'a-{uuid.uuid4().hex[:6]}@x.mg',
            password_hash=hash_password('x'),
            role=Role.ADMIN,
            tenant_id=tenant_a.id,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(user_a)
        db.session.commit()

        from app.websockets.socket_events import _tenant_belongs_to_user

        assert _tenant_belongs_to_user(tenant_a.id, user_a.id) is True
        assert _tenant_belongs_to_user(tenant_b.id, user_a.id) is False
        assert _tenant_belongs_to_user(99999, user_a.id) is False
        db.session.rollback()