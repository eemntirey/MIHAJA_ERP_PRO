import os

# Doit etre pose AVANT tout import de `app` : Config lit les variables
# PAPI_* au moment de l'import (attributs de classe), pas a l'appel.
os.environ.setdefault('PAPI_WEBHOOK_SECRET', 'test-webhook-secret')

# La suite de tests porte sur le serveur CENTRAL. Le fichier .env d'un poste de
# developpement peut contenir FLASK_ENV=local-embedded (backend embarque) :
# on fixe explicitement l'environnement AVANT l'import de `app` (l'app preserve
# les variables du processus, cf. app/__init__.py). Les tests du mode embarque
# creent leur propre application (voir tests/test_replication_full_cycle.py).
os.environ['FLASK_ENV'] = os.environ.get('TEST_FLASK_ENV', 'testing')

import pytest
from flask import request
from app import create_app, db as app_db
from app.models.utilisateur import Role
from app.services.replication import SUPPRESS_OUTBOX_KEY
from tests._db_utils import reset_schema as _reset_schema

# Neutralise le FLASK_ENV injecté au moment de l'import par
# `load_dotenv('.env.local', override=True)` (app/__init__.py) : sans cela, la
# suite pytest serait poussée en mode local-embedded (base locale + endpoints
# de réplication centraux absents -> 404). La suite tourne systématiquement
# sur la config 'testing' (SQLite en mémoire) ; les tests qui veulent du
# local-embedded le forcent explicitement via monkeypatch.
os.environ['FLASK_ENV'] = 'testing'


@pytest.fixture(scope='session')
def _db(app):
    """Alias session de la base de test."""
    return app_db


@pytest.fixture(autouse=True)
def _db_isolation(app):
    """Isole chaque test en nettoyant la session SQLAlchemy.

    - Avant le test : remove() pour partir sur une session propre, puis purge
      des tables de réplication (SQLite en mémoire = partagée entre les tests
      du même thread : sans cette purge, des entrées SyncOutbox/SyncCursor
      résiduelles faussent les comptages exacts de push et cassent les
      assertions `.one()` sur les curseurs).
    - Après le test : rollback + remove.  Pas de expire_all() en teardown
      car sur une session en erreur (InFailedSqlTransaction) ça peut
      déclencher des relectures DB qui échouent et casse les tests suivants.
    """
    _SYNC_TABLES = (
        'sync_outbox', 'sync_cursors', 'sync_conflicts',
        'sync_applied_keys', 'sync_state', 'sync_local_mappings',
        'sync_central_log',
    )
    with app.app_context():
        app_db.session.remove()
        try:
            from sqlalchemy import text as _text
            for _t in _SYNC_TABLES:
                app_db.session.execute(_text(f'DELETE FROM "{_t}"'))
            app_db.session.commit()
        except Exception:
            app_db.session.rollback()
        app_db.session.remove()
        yield
        try:
            app_db.session.rollback()
        except Exception:
            pass
        app_db.session.remove()


def _resolve_test_database_url():
    """Résout l'URL de la base de test.

    Priorité : TEST_DATABASE_URL > DATABASE_URL >
    postgresql+psycopg://postgres@localhost:55432/erp_test

    Si PostgreSQL n'est pas disponible (environnement local sans serveur
    55432), on bascule automatiquement vers SQLite en mémoire afin de
    permettre l'exécution des tests hors-ligne. Ce fallback est signalé via
    la variable d'environnement ``_DB_FALLBACK_SQLITE`` pour que les tests
    puissent s'adapter (ex : dialectes de SQL spécifique).
    """
    _base = os.getenv('TEST_DATABASE_URL') or os.getenv('DATABASE_URL') or \
        'postgresql+psycopg://postgres@localhost:55432/erp_test'
    _db_url = _base.rsplit('/', 1)[0] + '/erp_test'

    # Détecter si PostgreSQL est disponible ; sinon, fallback SQLite.
    if _db_url.startswith('postgresql'):
        try:
            import psycopg
            _uri = _db_url.replace('postgresql+psycopg://', 'postgresql://')[
                len('postgresql://'):]
            _host, _rest = _uri.split('@')
            _db = _rest.rsplit('/', 1)[-1]
            _h, _p = _host.rsplit(':', 1)
            with psycopg.connect(
                host=_h, port=_p.split('/')[0],
                dbname=_db, user='postgres', connect_timeout=3,
            ) as _conn:
                pass  # connexion OK → on garde PostgreSQL
        except Exception:
            # PostgreSQL inaccessible → fallback SQLite en mémoire.
            _db_url = 'sqlite:///:memory:'
            os.environ['_DB_FALLBACK_SQLITE'] = '1'
    return _db_url


@pytest.fixture(scope='session')
def app():
    # URL de test derivée de l'environnement (jamais de credential en dur :
    # un scan de secrets avait redigé cette ligne et casse toute la suite).
    _db_url = _resolve_test_database_url()
    os.environ['DATABASE_URL'] = _db_url
    os.environ['PAPI_API_URL'] = 'https://test.papi.mg/dashboard/api/payment-links'
    os.environ['PAPI_API_KEY'] = 'test-api-key'
    os.environ['PAPI_ENVIRONMENT'] = 'sandbox'
    os.environ['PAPI_CALLBACK_URL'] = 'http://localhost:5000/api/v1/papi/webhook'

    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}

    # En tests, le "serveur central" vit dans le même process/app que le poste.
    # Tant que test_outbox_hook a enregistré le listener outbox (module global,
    # sans filtre de bind), les INSERT appliqués par le central seraient
    # re-capturés puis re-poussés (boucle infinie). On neutralise la capture
    # pour les requêtes marquées X-Suppress-Outbox (miroir de la prod : un
    # serveur central n'a jamais de listener outbox local).
    @app.before_request
    def _suppress_outbox_for_central_requests():
        if request.headers.get('X-Suppress-Outbox', '').lower() in (
            '1', 'true', 'yes',
        ):
            app_db.session.info[SUPPRESS_OUTBOX_KEY] = True

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

    SQLAlchemy ne peut pas resoudre les cycles de ForeignKey dans le schema
    de production (``tenants`` <-> ``utilisateurs``, ``livreurs`` <->
    ``vehicules``, ``utilisateurs`` <-> ``roles``, plus les auto-referencess
    ``utilisateurs.created_by``/``updated_by``). Beaucoup de fichiers de
    tests appellent ``db.drop_all()`` directement ; on remplace la methode
    au niveau de la classe pour que le patch s'applique a toutes les
    instances et survive aux fixtures ``app`` redefinees localement.
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
def local_app(app):
    """Application de test jouant le role du poste (memes bases que le central).

    Les tests du mode reellement embarque (SQLite separe) creent leur propre
    application : voir tests/test_replication_full_cycle.py.
    """
    return app


@pytest.fixture
def replication_tenant(app):
    """Tenant reel utilise par les tests de replication (id non suppose).

    Beaucoup de fixtures ecrivaient `tenant_id=1` en dur : sur une base de test
    ou le tenant 1 n'existe pas, la contrainte de cle etrangere casse le test.
    """
    from app.models.tenant import StatutTenant, Tenant

    with app.app_context():
        tenant = Tenant.query.filter_by(slug='test-tenant-rep').first()
        if tenant is None:
            tenant = Tenant(
                nom='Tenant Replication',
                slug='test-tenant-rep',
                domaine='rep.local',
                statut=StatutTenant.ACTIF,
                plan='pro',
            )
            app_db.session.add(tenant)
            app_db.session.commit()
        return tenant.id


@pytest.fixture
def cached_local_user(app, replication_tenant):
    """Utilisateur local avec cache scrypt du mot de passe (login hors-ligne).

    Reproduit ce que fait le login en ligne du backend embarque :
    utilisateurs.local_password_hash est renseigne.
    """
    from app.models.utilisateur import Role, StatutUtilisateur, Utilisateur
    from app.security.auth import hash_password
    from app.services.local_auth import cache_local_credentials

    raw_password = 'secret123'
    with app.app_context():
        user = Utilisateur.query.filter_by(username='test_offline').first()
        if user is None:
            user = Utilisateur(
                username='test_offline',
                email='test_offline@local',
                password_hash=hash_password(os.urandom(24).hex()),
                role=Role.ADMIN,
                tenant_id=replication_tenant,
                statut=StatutUtilisateur.ACTIF,
            )
            app_db.session.add(user)
            app_db.session.commit()
        cache_local_credentials(user, raw_password)

        class CachedUser:
            id = user.id
            username = user.username
            tenant_id = user.tenant_id
            _raw_password = raw_password

        return CachedUser()


@pytest.fixture
def local_embedded_app(app, monkeypatch):
    """Application basculee en mode embarque, central volontairement injoignable.

    Sert aux tests du login hors-ligne (cache scrypt local) : REPLICATION_URL
    pointe sur un port ferme, donc le proxy echoue immediatement et le backend
    retombe sur le cache local.
    """
    monkeypatch.setitem(app.config, 'LOCAL_EMBEDDED', True)
    monkeypatch.setitem(app.config, 'REPLICATION_URL', 'http://127.0.0.1:1')
    monkeypatch.setitem(app.config, 'REPLICATION_DEVICE_ID', 'test-device')
    return app



@pytest.fixture
def db(app):
    with app.app_context():
        yield app_db
        app_db.session.rollback()


@pytest.fixture
def seeded_outbox(app, replication_tenant):
    """Cree UNE entree SyncOutbox en attente et renvoie une fonction d'acces.

    Les entrees residuelles sont supprimees au prealable : `push_pending` traite
    toute l'outbox, donc sans nettoyage les assertions `sent == 1` dependent de
    l'ordre d'execution des tests.
    """
    import uuid
    from app.models.sync_replica import SyncOutbox
    lu = str(uuid.uuid4())
    with app.app_context():
        SyncOutbox.query.delete()
        app_db.session.commit()
        entry = SyncOutbox(
            tenant_id=replication_tenant,
            device_id='test-device',
            entity='produit',
            op='INSERT',
            payload={'nom': 'ProduitTest', 'reference': 'REF-TEST-001'},
            local_uuid=lu,
            entity_pk=1,
            idempotency_key=f'test-device:{lu}',
            status='pending',
            attempts=0,
        )
        app_db.session.add(entry)
        app_db.session.commit()
    def _getter():
        with app.app_context():
            return SyncOutbox.query.filter_by(local_uuid=lu).first()
    return _getter


@pytest.fixture
def central_stub_ok(monkeypatch, app):
    """Stub simulant un serveur central qui renvoie 'applied'."""
    app.config['REPLICATION_URL'] = 'http://central.test'
    app.config['REPLICATION_DEVICE_ID'] = 'test-device'
    import requests
    class FakeResponse:
        ok = True
        def json(self):
            return {
                'results': [{
                    'local_uuid': 'test-uuid-001',
                    'status': 'applied',
                    'server_pk': 42,
                }]
            }
    monkeypatch.setattr(requests, 'post', lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: FakeResponse())
    return FakeResponse()


@pytest.fixture
def central_stub_error(monkeypatch, app):
    """Stub simulant un serveur central injoignable (erreur)."""
    app.config['REPLICATION_URL'] = 'http://central.test'
    app.config['REPLICATION_DEVICE_ID'] = 'test-device'
    import requests
    def _raise(*args, **kwargs):
        raise requests.ConnectionError("Serveur central injoignable")
    monkeypatch.setattr(requests, 'post', _raise)
    monkeypatch.setattr(requests, 'get', _raise)


@pytest.fixture
def central_stub_conflict(monkeypatch, app):
    """Stub simulant un serveur central qui renvoie un conflit."""
    app.config['REPLICATION_URL'] = 'http://central.test'
    app.config['REPLICATION_DEVICE_ID'] = 'test-device'
    import requests
    class ConflictResponse:
        ok = True
        def json(self):
            return {
                'results': [{
                    'local_uuid': 'test-uuid-001',
                    'status': 'conflict',
                    'server_pk': 99,
                    'remote_payload': {'nom': 'ProduitDistant'},
                }]
            }
    monkeypatch.setattr(requests, 'post', lambda *args, **kwargs: ConflictResponse())
    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: ConflictResponse())
    return ConflictResponse()


@pytest.fixture
def central_stub_changes(monkeypatch, app, replication_tenant):
    """Stub simulant un pull avec des modifications et un curseur existant."""
    app.config['REPLICATION_URL'] = 'http://central.test'
    app.config['REPLICATION_DEVICE_ID'] = 'test-device'
    app.config['LOCAL_TENANT_ID'] = replication_tenant
    import requests
    from app.models.sync_replica import SyncCursor, SyncLocalMapping
    with app.app_context():
        # Isolation : un seul curseur, aucune correspondance prealable.
        SyncCursor.query.delete()
        SyncLocalMapping.query.delete()
        app_db.session.commit()
        SyncCursor.upsert(
            tenant_id=replication_tenant, device_id='test-device',
            entity='produit', last_pulled_revision=0,
        )
    class PullResponse:
        ok = True
        def json(self):
            return {
                'revision': 100,
                'changes': [
                    {
                        'entity': 'produit',
                        'entity_pk': 1,
                        'op': 'INSERT',
                        # Payload realiste : le journal central contient la
                        # mutation complete (snake_case, comme to_dict()).
                        'payload': {
                            'reference': 'REF-PULL-001',
                            'nom': 'ProduitModifie',
                            'prix_vente_ht': 2500,
                            'tenant_id': replication_tenant,
                            'updated_at': '2026-09-21T12:00:00',
                        },
                        'revision': 100,
                        'source_device_id': 'autre-poste',
                    }
                ]
            }
    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: PullResponse())
    PullResponse.revision = 100
    return PullResponse()
