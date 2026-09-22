# Backend Local Embarqué (Desk 100% hors-ligne) — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre au desktop (Electron) de fonctionner 100% localement — même une semaine sans internet — en embarquant un backend Flask + SQLite local, répliqué vers le serveur central PostgreSQL dès le retour de la connexion.

**Architecture:** Le processus main d'Electron démarre un backend Flask local (exécutable PyInstaller en prod, `python run.py` en dev) écoutant sur `127.0.0.1:<port dynamique>`, avec SQLite stocké dans `app.getPath('userData')`. Le renderer parle TOUJOURS au backend local. Un module de réplication côté backend local pousse les mutations locales (outbox idempotent) et tire les deltas du central (curseur de révision) avec backoff exponentiel.

**Tech Stack:** Electron 38, Flask/SQLAlchemy existant, SQLite (`sqlite:///<userData>/erp-local.db`), PyInstaller, PostgreSQL central, Alembic, pytest.

**Spec:** Conversation du 21/09/2026 — « Option 1 : backend local + réplication local → central ». Contraintes AGENTS.md : multi-tenancy (`tenant_id` partout), messages en français, JWT `Authorization: Bearer` pour desk.

## Global Constraints

- Toutes les chaînes utilisateur et messages d'erreur en **français**.
- Chaque modèle répliqué conserve `tenant_id`.
- Idempotence stricte : `Idempotency-Key` (UUID) sur toute mutation répliquée ; le rejeu ne crée jamais de doublon (pattern existant `public.py` / `Checkout.jsx`).
- Le backend local ne peut JAMAIS écrire directement dans PostgreSQL central ; uniquement via le module de réplication HTTP.
- `FLASK_ENV=production` continue de refuser SQLite sur le central — seul le backend LOCAL utilise SQLite avec `FLASK_ENV=local-embedded`.
- Aucune modification de `shared/navConfig.js` ni du filtrage tenant existant.
- Tests : `cd web/backend && pytest` contre PostgreSQL `erp_test` (port 55432) ; le central est simulé par un serveur HTTP de test, pas de mock fragile.
- La file `syncEngine` existante reste pour les préférences desk (favoris/colonnes/filtres) ; les données métier passent par le backend local. Ne pas fusionner les deux.

## File Structure

```
web/backend/app/config/settings.py              # MODIFIER: classe LocalEmbeddedConfig
web/backend/app/models/sync_replica.py          # CREATE: SyncOutbox, SyncCursor, SyncConflict, SyncAppliedKey, SyncState
web/backend/app/services/replication/           # CREATE: __init__, outbox, push, pull, scheduler
web/backend/app/services/local_bootstrap.py     # CREATE: bootstrap idempotent base locale
web/backend/app/api/v1/replication.py           # CREATE: /sync/replicate/* (côté CENTRAL)
web/backend/app/api/v1/local_sync.py            # CREATE: /sync/local-status + /sync/conflicts (côté LOCAL)
web/backend/app/api/v1/__init__.py              # MODIFIER: enregistrer les namespaces
web/backend/migrations/versions/*_sync_replica.py  # CREATE
web/backend/run_local.py                        # CREATE: entrée PyInstaller
web/backend/tests/test_local_embedded_config.py, test_replication_models.py,
               test_outbox_hook.py, test_replication_endpoints.py,
               test_replication_engine.py, test_local_bootstrap.py,
               test_replication_full_cycle.py   # CREATE
desk/electron/backendHost.js                    # CREATE: spawn + supervision backend local
desk/electron/main.js, preload.js               # MODIFIER
desk/electron/backend/mihaja-backend.spec, build_backend.ps1  # CREATE
desk/package.json                               # MODIFIER: extraResources + scripts
shared/services/api.js                          # MODIFIER: baseURL = backend local
shared/components/SyncStatus/SyncStatus.jsx     # CREATE: badge d'état
```

---

### Task 1: Config `LocalEmbeddedConfig` (backend local SQLite)

**Files:**
- Modify: `web/backend/app/config/settings.py`
- Test: `web/backend/tests/test_local_embedded_config.py`

**Interfaces:**
- Produces: classe `LocalEmbeddedConfig` — `SQLALCHEMY_DATABASE_URI` SQLite fichier (via `LOCAL_DB_PATH`), `FLASK_ENV='local-embedded'`, `REPLICATION_URL` (URL du central), `REPLICATION_DEVICE_ID` (UUID), Celery/SocketIO désactivés. Factory de config : `FLASK_ENV == 'local-embedded'` → `LocalEmbeddedConfig`.

- [ ] **Step 1: Write the failing test**

```python
# web/backend/tests/test_local_embedded_config.py
import pytest

def test_local_embedded_config_uses_sqlite_file(monkeypatch, tmp_path):
    monkeypatch.setenv('FLASK_ENV', 'local-embedded')
    monkeypatch.setenv('LOCAL_DB_PATH', str(tmp_path / 'erp-local.db'))
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('REPLICATION_URL', 'https://erp.mihaja.mg')
    from app.config.settings import LocalEmbeddedConfig
    assert LocalEmbeddedConfig.SQLALCHEMY_DATABASE_URI.startswith('sqlite:///')
    assert 'erp-local.db' in LocalEmbeddedConfig.SQLALCHEMY_DATABASE_URI
    assert LocalEmbeddedConfig.REPLICATION_URL == 'https://erp.mihaja.mg'
    assert LocalEmbeddedConfig.REPLICATION_DEVICE_ID

def test_local_embedded_requires_replication_url(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'local-embedded')
    monkeypatch.delenv('REPLICATION_URL', raising=False)
    from app.config.settings import LocalEmbeddedConfig
    with pytest.raises(ValueError, match='REPLICATION_URL'):
        LocalEmbeddedConfig.validate()

def test_central_production_still_rejects_sqlite(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///erp.db')
    from app.config.settings import Config
    with pytest.raises(ValueError):
        Config.validate()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/backend && python -m pytest tests/test_local_embedded_config.py -v`
Expected: FAIL — `ImportError: cannot import name 'LocalEmbeddedConfig'`

- [ ] **Step 3: Write minimal implementation**

Dans `settings.py` (conserver `Config.validate()` existant tel quel) :

```python
class LocalEmbeddedConfig(Config):
    """Config du backend embarqué dans Electron (mode hors-ligne complet).

    SQLite local obligatoire ; les données métier sont répliquées vers le
    serveur central (REPLICATION_URL) par app/services/replication.
    """
    FLASK_ENV = 'local-embedded'
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.getenv('LOCAL_DB_PATH', '')}"
    REPLICATION_URL = os.getenv('REPLICATION_URL', '')
    REPLICATION_DEVICE_ID = os.getenv('REPLICATION_DEVICE_ID', str(uuid.uuid4()))
    CELERY_BROKER_URL = None
    ENABLE_SOCKETIO = False

    @classmethod
    def validate(cls):
        if not os.getenv('LOCAL_DB_PATH'):
            raise ValueError('LOCAL_DB_PATH est requis en mode local-embedded.')
        if not cls.REPLICATION_URL:
            raise ValueError(
                "REPLICATION_URL est requis en mode local-embedded "
                "(URL du serveur central pour la réplication)."
            )
```

Ajouter `import uuid` en tête si absent, et brancher la factory de config : `FLASK_ENV == 'local-embedded'` → `LocalEmbeddedConfig`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web/backend && python -m pytest tests/test_local_embedded_config.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add web/backend/app/config/settings.py web/backend/tests/test_local_embedded_config.py
git commit -m "feat(offline): config LocalEmbeddedConfig SQLite pour backend embarque"
```

---

### Task 2: Modèles de réplication (SyncOutbox / SyncCursor / SyncConflict)

**Files:**
- Create: `web/backend/app/models/sync_replica.py`
- Create: migration Alembic (autogénérée puis vérifiée)
- Test: `web/backend/tests/test_replication_models.py`

**Interfaces:**
- Produces:
  - `SyncOutbox` : `id, tenant_id, device_id, entity, entity_pk (nullable), local_uuid (unique), op ('INSERT'|'UPDATE'|'DELETE'), payload (JSON), idempotency_key (unique), status ('pending'|'sent'|'failed'|'conflict'), attempts, last_error, created_at, synced_at` + `SyncOutbox.record(tenant_id, device_id, entity, op, payload, local_uuid, entity_pk=None)`.
  - `SyncCursor` : `tenant_id, device_id, entity, last_pulled_revision` + `SyncCursor.upsert(tenant_id, device_id, entity, last_pulled_revision)`.
  - `SyncConflict` : `tenant_id, device_id, entity, entity_pk, local_payload, remote_payload, resolved_as, created_at`.
  - `SyncAppliedKey` (côté central) : `idempotency_key (unique), server_pk, entity, applied_at`.
  - `SyncState` (côté local, single-row id=1) : `online, pending_count, last_push_at, last_pull_at, last_error` + `SyncState.get_or_create()`.

- [ ] **Step 1: Write the failing test**

```python
# web/backend/tests/test_replication_models.py
import uuid
from app.models.sync_replica import SyncOutbox, SyncCursor

def test_record_creates_pending_outbox_entry(app, tenant_user):
    entry = SyncOutbox.record(
        tenant_id=tenant_user.tenant_id, device_id='device-1',
        entity='vente', op='INSERT',
        payload={'client': 'Rakoto', 'total': 15000},
        local_uuid=str(uuid.uuid4()),
    )
    assert entry.status == 'pending'
    assert entry.idempotency_key
    assert entry.attempts == 0

def test_record_is_idempotent_per_local_uuid(app, tenant_user):
    lu = str(uuid.uuid4())
    SyncOutbox.record(tenant_id=tenant_user.tenant_id, device_id='d1',
                      entity='vente', op='INSERT', payload={}, local_uuid=lu)
    dup = SyncOutbox.record(tenant_id=tenant_user.tenant_id, device_id='d1',
                            entity='vente', op='INSERT', payload={}, local_uuid=lu)
    assert dup.id is None  # existant retourné, pas recréé
    assert SyncOutbox.query.filter_by(local_uuid=lu).count() == 1

def test_cursor_upsert(app, tenant_user):
    SyncCursor.upsert(tenant_id=tenant_user.tenant_id, device_id='d1',
                      entity='produit', last_pulled_revision=42)
    SyncCursor.upsert(tenant_id=tenant_user.tenant_id, device_id='d1',
                      entity='produit', last_pulled_revision=50)
    cur = SyncCursor.query.filter_by(
        tenant_id=tenant_user.tenant_id, device_id='d1', entity='produit').one()
    assert cur.last_pulled_revision == 50
```

*(Fixture `tenant_user` : à créer dans `tests/conftest.py` si absente — utilisateur rattaché à un tenant.)*

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/backend && python -m pytest tests/test_replication_models.py -v`
Expected: FAIL — `ModuleNotFoundError: app.models.sync_replica`

- [ ] **Step 3: Write minimal implementation**

```python
# web/backend/app/models/sync_replica.py
# Modèles de réplication pour le mode hors-ligne desktop (backend embarqué).
from app import db
from datetime import datetime


class SyncOutbox(db.Model):
    __tablename__ = 'sync_outbox'
    # Pas de BaseModel : table locale au device, hors filtrage tenant ORM.
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)
    device_id = db.Column(db.String(64), nullable=False, index=True)
    entity = db.Column(db.String(64), nullable=False, index=True)
    entity_pk = db.Column(db.Integer, nullable=True)
    local_uuid = db.Column(db.String(36), nullable=False, unique=True)
    op = db.Column(db.String(10), nullable=False)  # INSERT|UPDATE|DELETE
    payload = db.Column(db.JSON, nullable=True)
    idempotency_key = db.Column(db.String(64), nullable=False, unique=True)
    status = db.Column(db.String(10), nullable=False, default='pending', index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    synced_at = db.Column(db.DateTime, nullable=True)

    @classmethod
    def record(cls, tenant_id, device_id, entity, op, payload, local_uuid, entity_pk=None):
        existing = cls.query.filter_by(local_uuid=local_uuid).first()
        if existing:
            return existing
        entry = cls(
            tenant_id=tenant_id, device_id=device_id, entity=entity,
            entity_pk=entity_pk, op=op, payload=payload, local_uuid=local_uuid,
            idempotency_key=f'{device_id}:{local_uuid}',
        )
        db.session.add(entry)
        db.session.commit()
        return entry


class SyncCursor(db.Model):
    __tablename__ = 'sync_cursors'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)
    device_id = db.Column(db.String(64), nullable=False, index=True)
    entity = db.Column(db.String(64), nullable=False, index=True)
    last_pulled_revision = db.Column(db.BigInteger, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'device_id', 'entity',
                            name='uq_sync_cursor_tenant_device_entity'),
    )

    @classmethod
    def upsert(cls, tenant_id, device_id, entity, last_pulled_revision):
        cur = cls.query.filter_by(
            tenant_id=tenant_id, device_id=device_id, entity=entity).first()
        if cur is None:
            cur = cls(tenant_id=tenant_id, device_id=device_id, entity=entity,
                      last_pulled_revision=last_pulled_revision)
            db.session.add(cur)
        else:
            cur.last_pulled_revision = max(cur.last_pulled_revision, last_pulled_revision)
        db.session.commit()
        return cur


class SyncConflict(db.Model):
    __tablename__ = 'sync_conflicts'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)
    device_id = db.Column(db.String(64), nullable=False)
    entity = db.Column(db.String(64), nullable=False)
    entity_pk = db.Column(db.Integer, nullable=True)
    local_payload = db.Column(db.JSON, nullable=True)
    remote_payload = db.Column(db.JSON, nullable=True)
    resolved_as = db.Column(db.String(20), nullable=False, default='pending_review')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class SyncAppliedKey(db.Model):
    """Côté central : clés d'idempotence déjà appliquées."""
    __tablename__ = 'sync_applied_keys'
    id = db.Column(db.Integer, primary_key=True)
    idempotency_key = db.Column(db.String(64), nullable=False, unique=True)
    entity = db.Column(db.String(64), nullable=False)
    server_pk = db.Column(db.Integer, nullable=False)
    applied_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class SyncState(db.Model):
    """Côté local : état de réplication (single-row, id=1)."""
    __tablename__ = 'sync_state'
    id = db.Column(db.Integer, primary_key=True, default=1)
    online = db.Column(db.Boolean, nullable=False, default=False)
    pending_count = db.Column(db.Integer, nullable=False, default=0)
    last_push_at = db.Column(db.DateTime, nullable=True)
    last_pull_at = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.Text, nullable=True)

    @classmethod
    def get_or_create(cls):
        s = cls.query.get(1)
        if s is None:
            s = cls(id=1)
            db.session.add(s)
            db.session.commit()
        return s
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web/backend && python -m pytest tests/test_replication_models.py -v`
Expected: PASS

- [ ] **Step 5: Migration + commit**

```bash
cd web/backend
flask --app 'app:create_app' db migrate -m "sync_replica outbox cursors conflicts"
flask --app 'app:create_app' db upgrade
python -m pytest tests/test_replication_models.py -v
git add app/models/sync_replica.py migrations/versions/ tests/test_replication_models.py
git commit -m "feat(offline): modeles SyncOutbox/SyncCursor/SyncConflict"
```

---

### Task 3: Outbox automatique (hook SQLAlchemy sur les mutations locales)

**Files:**
- Create: `web/backend/app/services/replication/__init__.py` (fichier vide)
- Create: `web/backend/app/services/replication/outbox.py`
- Modify: `web/backend/app/__init__.py` (enregistrer le listener UNIQUEMENT en `local-embedded`)
- Test: `web/backend/tests/test_outbox_hook.py`

**Interfaces:**
- Consumes: `SyncOutbox.record()` (Task 2).
- Produces: `register_outbox_listeners(db, entity_map)` où `entity_map = {'Produit': 'produit', 'Vente': 'vente', ...}` (classe modèle → nom entité). Listener `after_flush` sur `db.session` : capture INSERT/UPDATE/DELETE des modèles mappés → entrées outbox (`local_uuid` = UUID v4, `payload = <model>.to_dict()`).

- [ ] **Step 1: Write the failing test**

```python
# web/backend/tests/test_outbox_hook.py
from app import db
from app.models.sync_replica import SyncOutbox
from app.services.replication.outbox import register_outbox_listeners

def test_insert_creates_outbox_entry(app, tenant_user, produit_factory):
    register_outbox_listeners(db, {'Produit': 'produit'})
    p = produit_factory(nom='TestOffline', prix_unitaire=1000)
    entries = SyncOutbox.query.filter_by(entity='produit', op='INSERT').all()
    assert len(entries) == 1
    assert entries[0].payload['nom'] == 'TestOffline'
    assert entries[0].entity_pk == p.id

def test_update_creates_outbox_entry(app, tenant_user, produit_factory):
    register_outbox_listeners(db, {'Produit': 'produit'})
    p = produit_factory(nom='Avant', prix_unitaire=100)
    p.prix_unitaire = 200
    db.session.commit()
    upd = SyncOutbox.query.filter_by(entity='produit', op='UPDATE').one()
    assert upd.payload['prix_unitaire'] == 200

def test_delete_creates_outbox_entry(app, tenant_user, produit_factory):
    register_outbox_listeners(db, {'Produit': 'produit'})
    p = produit_factory(nom='ASupprimer', prix_unitaire=1)
    db.session.delete(p)
    db.session.commit()
    dele = SyncOutbox.query.filter_by(entity='produit', op='DELETE').one()
    assert dele.entity_pk == p.id
```

*(Fixture `produit_factory` : à créer dans `tests/conftest.py` si absente. Adapter le nom du modèle (`Produit`) au modèle réel du codebase.)*

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/backend && python -m pytest tests/test_outbox_hook.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.replication`

- [ ] **Step 3: Write minimal implementation**

```python
# web/backend/app/services/replication/outbox.py
# Capture automatique des mutations locales dans la SyncOutbox.
# Enregistré UNIQUEMENT sur le backend embarqué (FLASK_ENV=local-embedded),
# jamais sur le serveur central.
import uuid
from sqlalchemy import event
from app.models.sync_replica import SyncOutbox

_REGISTERED = False


def register_outbox_listeners(db, entity_map):
    """entity_map: {nom_de_classe_modele: nom_entity_outbox}"""
    global _REGISTERED
    if _REGISTERED:
        return
    targets = set(entity_map.keys())

    @event.listens_for(db.session, 'after_flush')
    def _capture(session, flush_context):
        device_id = session.info.get('device_id', 'default-device')
        for obj in list(session.new) + list(session.dirty) + list(session.deleted):
            cls = type(obj)
            name = targets and entity_map.get(cls.__name__)
            if not name:
                continue
            tenant_id = getattr(obj, 'tenant_id', None)
            if tenant_id is None:
                continue  # hors-scope (ex: SYNC_OUTBOX elle-même)
            if obj in session.deleted:
                op, payload, pk = 'DELETE', {'id': obj.id}, obj.id
            elif obj in session.new:
                op, payload, pk = 'INSERT', obj.to_dict(), obj.id
            elif session.is_modified(obj):
                op, payload, pk = 'UPDATE', obj.to_dict(), obj.id
            else:
                continue
            SyncOutbox.record(
                tenant_id=tenant_id, device_id=device_id, entity=name,
                op=op, payload=payload, local_uuid=str(uuid.uuid4()),
                entity_pk=pk,
            )
    _REGISTERED = True
```

Dans `app/__init__.py`, après `db.init_app(app)` :

```python
if app.config.get('FLASK_ENV') == 'local-embedded':
    from app.services.replication.outbox import register_outbox_listeners
    register_outbox_listeners(db, {
        'Produit': 'produit', 'Client': 'client', 'Vente': 'vente',
        'Fournisseur': 'fournisseur', 'CommandeAchat': 'commande_achat',
        # Liste à ajuster aux modèles métier réellement répliqués (V1:
        # produits, clients, ventes — le reste en V2).
    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web/backend && python -m pytest tests/test_outbox_hook.py tests/test_replication_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/backend/app/services/replication/ web/backend/app/__init__.py web/backend/tests/test_outbox_hook.py
git commit -m "feat(offline): outbox automatique via listeners SQLAlchemy (local uniquement)"
```

---

### Task 4: Endpoints de réplication côté serveur CENTRAL

**Files:**
- Create: `web/backend/app/api/v1/replication.py`
- Modify: `web/backend/app/api/v1/__init__.py` (enregistrer le namespace)
- Test: `web/backend/tests/test_replication_endpoints.py`

**Interfaces:**
- Produces (côté central, JWT requis + header `X-Device-Id`) :
  - `POST /api/v1/sync/replicate/push` — body `{mutations: [{entity, entity_pk, local_uuid, op, idempotency_key, payload, occurred_at}]}` → `{results: [{local_uuid, status: 'applied'|'duplicate'|'conflict', server_pk, remote_payload?}]}`. Idempotent : clé déjà appliquée → `duplicate` + `server_pk` d'origine. Conflit si `occurred_at` < `updated_at` serveur → `conflict` + payload serveur.
  - `GET /api/v1/sync/replicate/pull?since_revision=<n>&entities=produit,client` → `{revision: <max>, changes: [{entity, entity_pk, op, payload, revision}]}` (journal central `sync_central_log` alimenté dans la même transaction que chaque application).
  - `GET /api/v1/sync/replicate/status` → `{last_revision, server_time}`.

- [ ] **Step 1: Write the failing test**

```python
# web/backend/tests/test_replication_endpoints.py
import uuid

def _push_payload(local_uuid, entity='produit', pk=None):
    return {'mutations': [{
        'entity': entity, 'entity_pk': pk, 'local_uuid': local_uuid,
        'op': 'INSERT', 'idempotency_key': f'dev1:{local_uuid}',
        'payload': {'nom': 'ProduitLocal', 'prix_unitaire': 500},
        'occurred_at': '2026-09-21T10:00:00Z',
    }]}

def test_push_applies_and_returns_server_pk(client, auth_headers_tenant):
    r = client.post('/api/v1/sync/replicate/push',
                    json=_push_payload(str(uuid.uuid4())),
                    headers=auth_headers_tenant)
    assert r.status_code == 200, r.get_json()
    res = r.get_json()['results'][0]
    assert res['status'] == 'applied'
    assert res['server_pk'] > 0

def test_push_is_idempotent(client, auth_headers_tenant):
    key = str(uuid.uuid4())
    client.post('/api/v1/sync/replicate/push', json=_push_payload(key),
                headers=auth_headers_tenant)
    r2 = client.post('/api/v1/sync/replicate/push', json=_push_payload(key),
                     headers=auth_headers_tenant)
    assert r2.get_json()['results'][0]['status'] == 'duplicate'

def test_push_conflict_lww(client, auth_headers_tenant, produit_recent):
    # produit_recent.updated_at POSTERIEUR a occurred_at du payload
    r = client.post('/api/v1/sync/replicate/push', json=_push_payload(
        str(uuid.uuid4()), pk=produit_recent.id), headers=auth_headers_tenant)
    res = r.get_json()['results'][0]
    assert res['status'] == 'conflict'
    assert 'remote_payload' in res

def test_pull_returns_changes_since_revision(client, auth_headers_tenant):
    r = client.get('/api/v1/sync/replicate/pull?since_revision=0&entities=produit',
                   headers=auth_headers_tenant)
    body = r.get_json()
    assert 'revision' in body and 'changes' in body
```

*(Fixtures `auth_headers_tenant` (JWT d'un user de tenant) et `produit_recent` : à créer dans `tests/conftest.py`.)*

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/backend && python -m pytest tests/test_replication_endpoints.py -v`
Expected: FAIL — 404 sur `/sync/replicate/push`

- [ ] **Step 3: Write minimal implementation**

`web/backend/app/api/v1/replication.py` — namespace RESTx (suivre le style des namespaces existants dans `app/api/v1/`) :

```python
from flask_restx import Resource, reqparse
from app import db
from app.api.v1 import api
from app.models.sync_replica import SyncAppliedKey, SyncCentralLog
from app.models.produit import Produit  # etc. — registre d'entités ci-dessous
from flask_jwt_extended import jwt_required, get_jwt_identity

ns = api.namespace('sync/replicate', description='Réplication desktop -> central')

ENTITY_REGISTRY = {
    'produit': (Produit, ['nom', 'prix_unitaire', 'stock', 'categorie_id']),
    # V1 : produits/clients/ventes — via services métier pour Vente.
}

@ns.route('/push')
class ReplicationPush(Resource):
    @jwt_required()
    def post(self):
        tenant_id = _current_tenant_id()  # helper existant du codebase
        device_id = request.headers.get('X-Device-Id', 'unknown')
        results = []
        for m in request.get_json(force=True).get('mutations', []):
            applied = SyncAppliedKey.query.filter_by(
                idempotency_key=m['idempotency_key']).first()
            if applied:
                results.append({'local_uuid': m['local_uuid'],
                                'status': 'duplicate', 'server_pk': applied.server_pk})
                continue
            outcome = _apply_mutation(tenant_id, m)
            db.session.add(SyncAppliedKey(
                idempotency_key=m['idempotency_key'],
                entity=m['entity'], server_pk=outcome['server_pk'] or 0))
            results.append({'local_uuid': m['local_uuid'], **outcome})
        db.session.commit()
        return {'results': results}


def _apply_mutation(tenant_id, m):
    """Applique une mutation. Pour les INSERT/UPDATE produit : écriture ORM
    filtrée sur les colonnes autorisées. Pour les ventes : déléguer à
    vente_service avec l'idempotency_key pour préserver stock/facture/compta."""
    model, allowed_fields = ENTITY_REGISTRY[m['entity']]
    if m['op'] == 'INSERT':
        obj = model(tenant_id=tenant_id, **{k: v for k, v in m['payload'].items()
                                            if k in allowed_fields})
        db.session.add(obj)
        db.session.flush()
        _log_central(tenant_id, m, obj.id)
        return {'status': 'applied', 'server_pk': obj.id}
    existing = model.query.get(m['entity_pk'])
    if existing is None:
        return {'status': 'conflict', 'server_pk': None,
                'remote_payload': None, 'error': 'Entité introuvable côté central.'}
    if existing.updated_at and m.get('occurred_at'):
        from datetime import datetime
        if existing.updated_at > datetime.fromisoformat(
                m['occurred_at'].replace('Z', '+00:00')).replace_tzinfo(None):
            return {'status': 'conflict', 'server_pk': existing.id,
                    'remote_payload': existing.to_dict()}
    for k, v in m['payload'].items():
        if k in allowed_fields:
            setattr(existing, k, v)
    _log_central(tenant_id, m, existing.id)
    return {'status': 'applied', 'server_pk': existing.id}
```

Plus `GET /pull` : lit `SyncCentralLog.revision > since_revision` filtré tenant, renvoie `{revision, changes}`. Table `SyncCentralLog` : `id, tenant_id, entity, entity_pk, op, payload (JSON), revision (BigInteger auto via séquence/rowid)` — à ajouter dans `sync_replica.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web/backend && python -m pytest tests/test_replication_endpoints.py -v`
Expected: PASS

- [ ] **Step 5: Migration + commit**

```bash
cd web/backend
flask --app 'app:create_app' db migrate -m "sync_central_log"
flask --app 'app:create_app' db upgrade
python -m pytest tests/test_replication_endpoints.py -v
git add app/api/v1/replication.py app/api/v1/__init__.py app/models/sync_replica.py migrations/versions/ tests/test_replication_endpoints.py
git commit -m "feat(sync): endpoints replication push/pull idempotents cote central"
```

---

### Task 5: Moteur de réplication local (push + pull + scheduler avec backoff)

**Files:**
- Create: `web/backend/app/services/replication/push.py`
- Create: `web/backend/app/services/replication/pull.py`
- Create: `web/backend/app/services/replication/scheduler.py`
- Test: `web/backend/tests/test_replication_engine.py`

**Interfaces:**
- Consumes: `SyncOutbox`, `SyncCursor`, `SyncState` (Task 2) ; endpoints du Task 4.
- Produces:
  - `push_pending(app) -> {'sent': int, 'remaining': int}` — lit outbox `pending`/`failed` (max 100/cycle), POST au central, marque `sent`/`conflict`, incrément `attempts`/`last_error`.
  - `pull_changes(app) -> {'applied': int, 'revision': int}` — pour chaque entité du curseur : GET pull, application LWW, avance du curseur.
  - `start_replication_scheduler(app, interval_s=60)` — thread daemon ; si central joignable → push puis pull ; backoff `[30, 60, 120, 300, 600, 1800]` reset au succès ; met à jour `SyncState`.
  - `sync_state` exposé par `GET /api/v1/sync/local-status` (Task 9).

- [ ] **Step 1: Write the failing test**

```python
# web/backend/tests/test_replication_engine.py
# Fixtures: local_app (FLASK_ENV=local-embedded + SQLite tmp), central_stub
# (serveur HTTP de test sur port éphémere simulant /sync/replicate/push|pull).

def test_push_marks_sent_on_success(local_app, seeded_outbox, central_stub_ok):
    from app.services.replication.push import push_pending
    report = push_pending(local_app)
    assert report['sent'] == 1
    assert seeded_outbox().status == 'sent'

def test_push_marks_failed_and_increments_attempts(local_app, seeded_outbox, central_stub_error):
    from app.services.replication.push import push_pending
    push_pending(local_app)
    e = seeded_outbox()
    assert e.status == 'failed'
    assert e.attempts == 1 and e.last_error

def test_pull_advances_cursor_and_applies_changes(local_app, central_stub_changes):
    from app.services.replication.pull import pull_changes
    report = pull_changes(local_app)
    assert report['applied'] >= 1
    from app.models.sync_replica import SyncCursor
    cur = SyncCursor.query.filter_by(entity='produit').one()
    assert cur.last_pulled_revision == central_stub_changes.revision

def test_conflict_recorded_on_conflict_response(local_app, seeded_outbox, central_stub_conflict):
    from app.services.replication.push import push_pending
    push_pending(local_app)
    from app.models.sync_replica import SyncConflict
    assert SyncConflict.query.count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/backend && python -m pytest tests/test_replication_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.replication.push`

- [ ] **Step 3: Write minimal implementation**

```python
# web/backend/app/services/replication/push.py
import requests
from datetime import datetime
from flask import current_app
from app import db
from app.models.sync_replica import SyncOutbox, SyncConflict, SyncState

MAX_BATCH = 100


def push_pending(app):
    with app.app_context():
        base = current_app.config['REPLICATION_URL'].rstrip('/')
        token = current_app.extensions.get('repl_token')
        device_id = current_app.config['REPLICATION_DEVICE_ID']
        entries = SyncOutbox.query.filter(
            SyncOutbox.status.in_(['pending', 'failed'])).limit(MAX_BATCH).all()
        sent = 0
        for e in entries:
            try:
                r = requests.post(f'{base}/api/v1/sync/replicate/push', json={
                    'mutations': [{
                        'entity': e.entity, 'entity_pk': e.entity_pk,
                        'local_uuid': e.local_uuid, 'op': e.op,
                        'idempotency_key': e.idempotency_key,
                        'payload': e.payload,
                        'occurred_at': e.created_at.isoformat(),
                    }]},
                    headers={'Authorization': f'Bearer {token}',
                             'X-Device-Id': device_id}, timeout=15)
                res = r.json()['results'][0]
                if res['status'] in ('applied', 'duplicate'):
                    e.status, e.synced_at, sent = 'sent', datetime.utcnow(), sent + 1
                elif res['status'] == 'conflict':
                    e.status = 'conflict'
                    db.session.add(SyncConflict(
                        tenant_id=e.tenant_id, device_id=e.device_id,
                        entity=e.entity, entity_pk=e.entity_pk,
                        local_payload=e.payload,
                        remote_payload=res.get('remote_payload'),
                        resolved_as='remote_wins'))
            except Exception as exc:
                e.status, e.attempts = 'failed', e.attempts + 1
                e.last_error = str(exc)[:500]
            db.session.commit()
        state = SyncState.get_or_create()
        state.pending_count = SyncOutbox.query.filter_by(
            status='pending').count() + SyncOutbox.query.filter_by(status='failed').count()
        state.last_push_at = datetime.utcnow()
        db.session.commit()
        return {'sent': sent, 'remaining': state.pending_count}
```

`pull.py` : pour chaque ligne du curseur → `GET {base}/api/v1/sync/replicate/pull?since_revision=<cur>&entities=<entity>` ; pour chaque change : si `op == 'DELETE'` → soft-delete local ; sinon LWW : appliquer uniquement si `change.payload.updatedAt > local.updatedAt` (écriture ORM filtrée sur colonnes autorisées, même registre que le Task 4) ; puis `SyncCursor.upsert(..., report['revision'])` et mise à jour `SyncState.last_pull_at`.

```python
# web/backend/app/services/replication/scheduler.py
import threading
import time

BACKOFFS = [30, 60, 120, 300, 600, 1800]


def start_replication_scheduler(app, interval_s=60):
    def _loop():
        backoff_idx = 0
        while True:
            try:
                from app.services.replication.push import push_pending
                from app.services.replication.pull import pull_changes
                push_pending(app)
                pull_changes(app)
                backoff_idx = 0
                wait = interval_s
            except Exception:
                wait = BACKOFFS[min(backoff_idx, len(BACKOFFS) - 1)]
                backoff_idx += 1
            time.sleep(wait)
    t = threading.Thread(target=_loop, daemon=True, name='replication-scheduler')
    t.start()
    return t
```

Brancher `start_replication_scheduler(app)` dans `run_local.py` / `run.py` quand `FLASK_ENV == 'local-embedded'`. Le JWT de service (`repl_token`) est obtenu au login local réussi (login proxifié vers le central) et rafraîchi par le scheduler.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web/backend && python -m pytest tests/test_replication_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/backend/app/services/replication/ web/backend/tests/test_replication_engine.py
git commit -m "feat(offline): moteur replication push/pull avec backoff et conflits LWW"
```

---

### Task 6: Lancement du backend local par Electron

**Files:**
- Create: `desk/electron/backendHost.js`
- Modify: `desk/electron/main.js`
- Modify: `desk/electron/preload.js`
- Modify: `shared/services/api.js`

**Interfaces:**
- Produces (process main) : `startLocalBackend() -> Promise<{port, pid}>`, `stopLocalBackend()`, `getPort()`, `onStatus(cb)` ; événements renderer `backend:status` ('starting'|'ready'|'error'|'stopped') ; IPC `backend:port`, `backend:config-get`, `backend:config-set`.
- Produces (renderer) : port du backend transmis via query param `?backendPort=<n>` de l'URL chargée — `shared/services/api.js` le lit de façon **synchrone** au démarrage (pas de course).

- [ ] **Step 1: Écrire backendHost.js**

```javascript
// desk/electron/backendHost.js
// Démarre et supervise le backend Flask local embarqué.
// - Dev  : spawn `python run.py` du backend avec env local-embedded.
// - Prod : spawn l'exécutable PyInstaller packagé (resources/backend/).
// Port dynamique (allocation éphémère) pour éviter tout conflit.
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');
const fs = require('fs');
const { app, BrowserWindow } = require('electron');

let backendProc = null;
let currentPort = null;

function getFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.listen(0, '127.0.0.1', () => {
      const port = srv.address().port;
      srv.close(() => resolve(port));
    });
    srv.on('error', reject);
  });
}

function emitStatus(status) {
  BrowserWindow.getAllWindows().forEach((w) =>
    w.webContents.send('backend:status', status));
}

function readUserConfig() {
  const cfgPath = path.join(app.getPath('userData'), 'local-backend.json');
  try {
    return JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  } catch { return {}; }
}

async function startLocalBackend() {
  const port = await getFreePort();
  const dbDir = path.join(app.getPath('userData'), 'local-db');
  fs.mkdirSync(dbDir, { recursive: true });
  const cfg = readUserConfig();
  const isDev = process.env.ELECTRON_DEV === '1' || !app.isPackaged;
  const backendRoot = isDev
    ? path.join(__dirname, '..', '..', 'web', 'backend')
    : path.join(process.resourcesPath, 'backend');

  const env = {
    ...process.env,
    FLASK_ENV: 'local-embedded',
    LOCAL_DB_PATH: path.join(dbDir, 'erp-local.db'),
    LOCAL_API_PORT: String(port),
    REPLICATION_URL: cfg.replicationUrl || process.env.REPLICATION_URL || 'https://erp.mihaja.mg',
    SECRET_KEY: cfg.secretKey || 'local-embedded-secret-a-remplacer',
    JWT_SECRET_KEY: cfg.jwtSecretKey || 'local-embedded-jwt-a-remplacer',
  };

  backendProc = isDev
    ? spawn('python', ['run.py'], { cwd: backendRoot, env, shell: true })
    : spawn(path.join(backendRoot, 'mihaja-backend.exe'), [], { env });
  emitStatus('starting');
  backendProc.on('exit', () => { backendProc = null; emitStatus('stopped'); });

  // Health-check : /health doit répondre avant de déclarer 'ready'
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/health`);
      if (r.ok) { emitStatus('ready'); return { port, pid: backendProc.pid }; }
    } catch { /* pas encore prêt */ }
    await new Promise((r) => setTimeout(r, 500));
  }
  emitStatus('error');
  throw new Error("Le serveur local n'a pas démarré dans les 20 secondes.");
}

function stopLocalBackend() {
  if (backendProc) { backendProc.kill(); backendProc = null; }
}
function getPort() { return currentPort; }

module.exports = { startLocalBackend, stopLocalBackend, getPort };
// NB: conserver `currentPort = port;` juste après l'allocation (ligne manquante
// volontairement signalée ici pour l'implémenteur : l'ajouter).
```

- [ ] **Step 2: Intégrer dans main.js + preload.js + api.js**

Dans `main.js` (process main, après `app.whenReady()`) :

```javascript
const backendHost = require('./backendHost');

app.whenReady().then(async () => {
  Menu.setApplicationMenu(buildMenu());
  registerSecureStoreHandlers();
  let port = null;
  try {
    const started = await backendHost.startLocalBackend();
    port = started.port;
  } catch (err) {
    // La fenêtre s'ouvre quand même : écran d'erreur géré côté renderer.
    dialog.showErrorBox(
      'Erreur de démarrage',
      "Impossible de démarrer le serveur local.\n" + String(err));
  }
  createWindow(port);
  // ...
});

app.on('before-quit', () => backendHost.stopLocalBackend());

ipcMain.handle('backend:port', () => backendHost.getPort());
```

`createWindow(port)` : passer le port à l'URL chargée —

```javascript
if (isDev) {
  win.loadURL(port ? `${DEV_URL}/?backendPort=${port}` : DEV_URL);
} else {
  win.loadFile(path.join(__dirname, '..', 'build', 'index.html'),
    port ? { query: { backendPort: String(port) } } : {});
}
```

Dans `preload.js` (contextBridge existant) :

```javascript
contextBridge.exposeInMainWorld('electron', {
  secureStore: { /* existant, inchangé */ },
  backend: {
    getPort: () => ipcRenderer.invoke('backend:port'),
  },
});
```

Dans `shared/services/api.js` — remplacer la déclaration de `RAW_API_BASE_URL` (le port est connu de façon synchrone au premier rendu) :

```javascript
const backendPort = (typeof window !== 'undefined'
  && new URLSearchParams(window.location.search).get('backendPort')) || null;

const RAW_API_BASE_URL = backendPort
    ? `http://127.0.0.1:${backendPort}/api/v1`
    : (import.meta.env.VITE_API_URL || '/api/v1');
```

⚠️ Ajuster aussi `socketClient.js` (SOCKET_URL dérivé de `API_BASE_URL`) : en mode embarqué, le socket local est désactivé (`ENABLE_SOCKETIO=False`) — garder un fallback polling ou ne pas connecter le socket si `backendPort` est présent.

- [ ] **Step 3: Test manuel de vérification**

```bash
cd desk && npm run electron:dev
```
Expected : la fenêtre Electron s'ouvre ; DevTools → onglet Réseau : les requêtes partent vers `http://127.0.0.1:<port>/api/v1/...` ; couper le Wi-Fi → l'UI reste fonctionnelle ; fermer l'app → le process `python` est tué (vérifier dans le gestionnaire des tâches).

- [ ] **Step 4: Commit**

```bash
git add desk/electron/backendHost.js desk/electron/main.js desk/electron/preload.js shared/services/api.js
git commit -m "feat(desk): backend Flask local embarque demarre par Electron"
```

---

### Task 7: Provisionnement de la base locale + login hors-ligne

**Files:**
- Create: `web/backend/app/services/local_bootstrap.py`
- Modify: `web/backend/run.py` (bootstrap + port local + scheduler)
- Test: `web/backend/tests/test_local_bootstrap.py`

**Interfaces:**
- Produces: `ensure_local_db_ready(app)` — idempotent : `db.create_all()` si première exécution + `stamp head` + seed rôles. Login local : si central joignable → proxifier et cacher un hash scrypt du mot de passe dans `utilisateurs.local_password_hash` (colonne locale) ; si central injoignable → vérifier contre ce hash (message français si échec).

- [ ] **Step 1: Write the failing test**

```python
# web/backend/tests/test_local_bootstrap.py
def test_bootstrap_creates_tables_and_roles(local_app):
    from app.services.local_bootstrap import ensure_local_db_ready
    ensure_local_db_ready(local_app)
    with local_app.app_context():
        from sqlalchemy import inspect
        tables = inspect(local_app.db.engine).get_table_names()
        assert 'utilisateurs' in tables
        assert 'sync_outbox' in tables

def test_bootstrap_is_idempotent(local_app):
    from app.services.local_bootstrap import ensure_local_db_ready
    ensure_local_db_ready(local_app)
    ensure_local_db_ready(local_app)  # pas d'erreur, pas de doublon de rôles

def test_offline_login_uses_cached_credentials(local_app, cached_local_user):
    # cached_local_user: utilisateur avec local_password_hash renseigné
    client = local_app.test_client()
    r = client.post('/api/v1/auth/login',
                    json={'username': cached_local_user.username,
                          'password': cached_local_user._raw_password})
    assert r.status_code == 200
    assert r.get_json()['offline'] is True

def test_offline_login_rejects_wrong_password(local_app, cached_local_user):
    client = local_app.test_client()
    r = client.post('/api/v1/auth/login',
                    json={'username': cached_local_user.username,
                          'password': 'mauvais-mot-de-passe'})
    assert r.status_code == 401
    assert 'hors-ligne' in r.get_json()['message'].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/backend && python -m pytest tests/test_local_bootstrap.py -v`
Expected: FAIL — module inexistant

- [ ] **Step 3: Implémentation**

```python
# web/backend/app/services/local_bootstrap.py
# Bootstrap idempotent de la base locale embarquée (FLASK_ENV=local-embedded).
from sqlalchemy import inspect as sa_inspect


def ensure_local_db_ready(app):
    with app.app_context():
        from app import db
        from flask_migrate import stamp
        tables = sa_inspect(db.engine).get_table_names()
        if 'alembic_version' not in tables:
            db.create_all()
            stamp(revision='head')
        # Seed rôles : réutiliser la logique idempotente existante du backend
        # (seed auto quand la table roles est vide — cf. AGENTS.md).
        from app.services.seed import seed_roles_if_empty
        seed_roles_if_empty()
```

Dans `run.py` (avant `app.run`) :

```python
import os
if os.getenv('FLASK_ENV') == 'local-embedded':
    from app.services.local_bootstrap import ensure_local_db_ready
    from app.services.replication.scheduler import start_replication_scheduler
    ensure_local_db_ready(app)
    start_replication_scheduler(app)
    app.run(host='127.0.0.1',
            port=int(os.getenv('LOCAL_API_PORT', '5000')))
else:
    # comportement actuel inchangé
    ...
```

Login hors-ligne (dans le service auth existant, branche `local-embedded`) : hash `scrypt` (`hashlib.scrypt(pwd, salt=DEVICE_ID, n=16384, r=8, p=1)`) stocké localement au login proxifié ; en offline, comparaison directe. Message d'échec : « Identifiants incorrects (mode hors-ligne : seule la dernière session enregistrée peut se connecter). »

- [ ] **Step 4: Run test + commit**

```bash
cd web/backend && python -m pytest tests/test_local_bootstrap.py -v
git add app/services/local_bootstrap.py run.py tests/test_local_bootstrap.py
git commit -m "feat(offline): bootstrap base locale + login hors-ligne"
```

---

### Task 8: Bundle PyInstaller + packaging electron-builder

**Files:**
- Create: `web/backend/run_local.py`
- Create: `desk/electron/backend/mihaja-backend.spec`
- Create: `desk/electron/backend/build_backend.ps1`
- Modify: `desk/package.json`

**Interfaces:**
- Produces: `mihaja-backend.exe` (one-file PyInstaller) inclus dans l'installeur NSIS via `extraResources` → chargé par `backendHost.js` en mode packagé.

- [ ] **Step 1: Entrée PyInstaller**

```python
# web/backend/run_local.py
# Entrée du backend embarqué (packagé par PyInstaller pour le desktop).
import os
from app import create_app
from app.services.local_bootstrap import ensure_local_db_ready
from app.services.replication.scheduler import start_replication_scheduler

app = create_app()
ensure_local_db_ready(app)
start_replication_scheduler(app)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.getenv('LOCAL_API_PORT', '5000')))
```

```python
# desk/electron/backend/mihaja-backend.spec
a = Analysis(
    ['../../web/backend/run_local.py'],
    pathex=['../../web/backend'],
    datas=[('../../web/backend/migrations', 'migrations')],
    hiddenimports=['app', 'app.models', 'app.api.v1', 'engineio.async_drivers'],
    excludes=['tkinter', 'pytest'],
)
exe = EXE(pyz, a, name='mihaja-backend', console=False, one_file=True)
```

- [ ] **Step 2: Script de build + electron-builder**

```powershell
# desk/electron/backend/build_backend.ps1
# Build du backend embarque (PyInstaller) dans desk/electron/backend/dist.
$ErrorActionPreference = 'Stop'
$root = Resolve-Path "$PSScriptRoot\..\..\.."
$venvPy = "$root\web\backend\venv\Scripts\python.exe"
& $venvPy -m pip install pyinstaller --quiet
Push-Location "$root\desk\electron\backend"
& $venvPy -m PyInstaller mihaja-backend.spec --distpath dist --workpath build --noconfirm
Pop-Location
Write-Host "Backend embarque construit: desk/electron/backend/dist/mihaja-backend.exe"
```

`desk/package.json` — ajouter dans `build` et `scripts` :

```json
"build": {
  "extraResources": [{ "from": "electron/backend/dist", "to": "backend" }]
},
"scripts": {
  "build:backend": "powershell -ExecutionPolicy Bypass -File electron/backend/build_backend.ps1",
  "dist:offline": "npm run build && npm run build:backend && electron-builder"
}
```

⚠️ `.gitignore` : ajouter `desk/electron/backend/dist/` et `desk/electron/backend/build/` (l'exe ne se committe pas, il se construit en CI ou avant release).

- [ ] **Step 3: Vérification**

```bash
cd desk && npm run dist:offline
# Installer le NSIS généré sur une machine propre (ou VM), lancer SANS internet :
# login local OK, création produit/vente OK, données visibles et persistantes
# après redémarrage (SQLite dans %APPDATA%/erp-frontend-desk/local-db/).
```

- [ ] **Step 4: Commit**

```bash
git add web/backend/run_local.py desk/electron/backend/mihaja-backend.spec desk/electron/backend/build_backend.ps1 desk/package.json .gitignore
git commit -m "build(desk): bundle backend PyInstaller + extraResources electron-builder"
```

---

### Task 9: Indicateur d'état de réplication dans l'UI

**Files:**
- Create: `web/backend/app/api/v1/local_sync.py`
- Modify: `web/backend/app/api/v1/__init__.py`
- Create: `shared/components/SyncStatus/SyncStatus.jsx`
- Modify: topbar/layout du desk (intégrer le badge)

**Interfaces:**
- Consumes: `SyncState` (Task 2, alimenté par le scheduler Task 5) ; IPC `backend:status`.
- Produces: `GET /api/v1/sync/local-status` (JWT requis) → `{online, pending_count, last_push_at, last_pull_at, last_error}`. Composant `<SyncStatus/>` : 🟢 « Synchronisé » / 🟡 « X modifications en attente » / 🔴 « Hors-ligne — données locales uniquement ». Rendu `null` sur le web (pas de `window.electron.backend`) pour ne rien changer au comportement web.

- [ ] **Step 1: Endpoint local**

```python
# web/backend/app/api/v1/local_sync.py
from flask_restx import Resource
from flask_jwt_extended import jwt_required
from app.api.v1 import api

ns = api.namespace('sync', description='Etat de synchronisation locale')

@ns.route('/local-status')
class LocalSyncStatus(Resource):
    @jwt_required()
    def get(self):
        from app.models.sync_replica import SyncState
        s = SyncState.get_or_create()
        return {
            'online': s.online,
            'pending_count': s.pending_count,
            'last_push_at': s.last_push_at.isoformat() if s.last_push_at else None,
            'last_pull_at': s.last_pull_at.isoformat() if s.last_pull_at else None,
            'last_error': s.last_error,
        }
```

- [ ] **Step 2: Composant React**

```jsx
// shared/components/SyncStatus/SyncStatus.jsx
import React, { useEffect, useState } from 'react';
import api from '../services/api';

// Badge d'état de réplication — uniquement sur le desktop embarqué.
// États: ready (vert), pending (jaune), offline/starting (rouge).
export default function SyncStatus() {
  const [state, setState] = useState(null);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.electron?.backend) return undefined;
    let alive = true;
    const poll = async () => {
      try {
        const { data } = await api.get('/sync/local-status');
        if (alive) setState({ ...data, reachable: true });
      } catch {
        if (alive) setState({ reachable: false, pending_count: '?' });
      }
    };
    poll();
    const id = setInterval(poll, 30000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  if (!state) return null; // web ou backend non embarqué
  const label = !state.reachable
    ? 'Serveur local injoignable'
    : !state.online
      ? 'Hors-ligne — données locales uniquement'
      : state.pending_count > 0
        ? `${state.pending_count} modification(s) en attente`
        : 'Synchronisé';
  const color = !state.reachable || !state.online ? '#ef4444'
    : state.pending_count > 0 ? '#f59e0b' : '#22c55e';
  return (
    <span className="sync-status" title={label} style={{ color }}>
      ● {label}
    </span>
  );
}
```

- [ ] **Step 3: Test manuel + commit**

Lancer desk avec internet → 🟢 « Synchronisé ». Couper le réseau, créer une vente → 🟡 « 1 modification en attente ». Rétablir le réseau → retour 🟢 et la vente visible sur le central (`GET /api/v1/ventes` côté central). Vérifier que le web ne rend rien (badge absent).

```bash
git add web/backend/app/api/v1/local_sync.py web/backend/app/api/v1/__init__.py shared/components/SyncStatus/
git commit -m "feat(desk): indicateur d'etat de synchronisation hors-ligne"
```

---

### Task 10: Écran de conflits + cycle complet testé

**Files:**
- Create: `web/backend/app/api/v1/sync_conflicts.py` (côté local : `GET /sync/conflicts`, `POST /sync/conflicts/<id>/resolve`)
- Modify: `web/backend/app/api/v1/__init__.py`
- Create: page conflits minimale dans desk
- Test: `web/backend/tests/test_replication_full_cycle.py`

**Interfaces:**
- Consumes: `SyncConflict` (Task 2), `push_pending` (Task 5).
- Produces: `POST /sync/conflicts/<id>/resolve` body `{resolution: 'local_wins'|'remote_wins'}` — `local_wins` re-pousse le payload local avec priorité forcée (header `X-Force-Win: true` accepté par le central, loggé en audit) ; `remote_wins` applique le payload distant localement.

- [ ] **Step 1: Test de cycle complet (test d'acceptation du projet)**

```python
# web/backend/tests/test_replication_full_cycle.py
# Scénario E2E :
# 1. Le central contient des produits            (central seed)
# 2. Le local pull ces produits                  (pull_changes)
# 3. Coupure réseau                              (central_stub.down())
# 4. Une vente est créée en local                (POST /api/v1/ventes local)
# 5. Le stock local est décrémenté               (assert local)
# 6. Retour du réseau                            (central_stub.up())
# 7. Le scheduler pousse la vente                (push_pending)
# 8. La vente existe sur le central avec le même local_uuid appliqué,
#    et le stock central est décrémenté UNE SEULE FOIS (idempotence critique).
def test_full_offline_cycle(local_app, central_app, central_stub, seeded_outbox_factory):
    ...
    # assertions finales :
    # - vente présente sur central (server_pk > 0)
    # - second push du même local_uuid -> 'duplicate' (pas de 2e décrémentation)
    # - stock central == stock local
```

- [ ] **Step 2: Résolution de conflit (endpoint local)**

```python
# web/backend/app/api/v1/sync_conflicts.py (extrait)
@ns.route('/conflicts')
class ConflictList(Resource):
    @jwt_required()
    def get(self):
        rows = SyncConflict.query.order_by(SyncConflict.created_at.desc()).all()
        return {'conflicts': [{
            'id': c.id, 'entity': c.entity, 'entity_pk': c.entity_pk,
            'local_payload': c.local_payload, 'remote_payload': c.remote_payload,
            'resolved_as': c.resolved_as,
            'created_at': c.created_at.isoformat(),
        } for c in rows]}

@ns.route('/conflicts/<int:conflict_id>/resolve')
class ConflictResolve(Resource):
    @jwt_required()
    def post(self, conflict_id):
        c = SyncConflict.query.get_or_404(conflict_id)
        resolution = (request.get_json() or {}).get('resolution')
        if resolution == 'local_wins':
            # re-pousser avec priorité forcée via le moteur push (X-Force-Win)
            from app.services.replication.push import force_push_conflict
            force_push_conflict(c)
            c.resolved_as = 'local_wins'
        elif resolution == 'remote_wins':
            _apply_remote_payload(c)
            c.resolved_as = 'remote_wins'
        else:
            return {'message': 'resolution doit etre local_wins ou remote_wins'}, 400
        db.session.commit()
        return {'id': c.id, 'resolved_as': c.resolved_as}
```

- [ ] **Step 3: Suite complète + smoke test**

```bash
cd web/backend && python -m pytest -v        # toute la suite verte
cd desk && npm run electron:dev              # smoke : offline 24h si possible,
                                             # puis reconnexion et contrôle central
```

- [ ] **Step 4: Commit final + graphify**

```bash
git add web/backend/app/api/v1/sync_conflicts.py web/backend/app/api/v1/__init__.py web/backend/tests/test_replication_full_cycle.py desk/src/
git commit -m "feat(offline): resolution de conflits + cycle complet offline teste"
graphify update .
```

---

## Risques & points de vigilance

1. **Idempotence du stock** : la décrémentation de stock au rejeu d'une vente est LE risque de doublon. Le central doit appliquer les ventes via `vente_service` avec l'`Idempotency-Key` vérifiée DANS la même transaction que la décrémentation (`with_for_update()` existant).
2. **Horloge locale fausse** : le LWW repose sur `updatedAt`/`occurredAt` — une horloge de poste qui dérive tranche les conflits à tort. Mitigation : utiliser l'heure serveur reçue au pull comme référence et alerter si l'écart local/serveur dépasse 5 minutes.
3. **Taille de la base locale** : une semaine de ventes en SQLite est confortable (milliers de lignes), mais prévoir une purge de l'outbox `sent` > 30 jours.
4. **Sécurité du poste local** : la base SQLite locale n'est pas chiffrée. Pour des postes partagés, envisager SQLCipher (extension de ce plan, non bloquant en V1).
5. **Listener outbox (Task 3)** : `after_flush` committe par entrée — acceptable en local mono-utilisateur ; passer en batch si la performance se dégrade sur de gros imports.
6. **Deux sources de vérité des PK** : les ids locaux SQLite ≠ ids centraux PostgreSQL. Toute référence croisée (ex: `vente.produit_id`) doit être résolue via le mapping `local_uuid ↔ server_pk` maintenu par `SyncAppliedKey` au push et par le pull côté local.

## Estimation

| Task | Description | Effort estimé |
|---|---|---|
| 1 | Config local-embedded | 0,5 j |
| 2 | Modèles réplication | 1 j |
| 3 | Outbox hook | 1 j |
| 4 | Endpoints central | 1,5 j |
| 5 | Moteur push/pull/scheduler | 2 j |
| 6 | Intégration Electron | 1,5 j |
| 7 | Bootstrap + login offline | 1,5 j |
| 8 | Packaging PyInstaller | 1,5 j |
| 9 | Badge UI | 0,5 j |
| 10 | Conflits + E2E | 2 j |
| **Total** | | **~13 j** (MVP : Tasks 1–2, 4–7 = ~8 j pour un offline opérationnel sur produits/clients/ventes) |















