# web/backend/tests/test_replication_full_cycle.py
# Cycle complet hors-ligne : pull initial -> mutation locale (outbox) -> push
# vers le central -> re-push idempotent (pas de doublon côté central).
#
# Le « central » est la VRAIE application Flask (mêmes endpoints que la
# production) atteinte via un adaptateur requests -> test_client : aucun mock
# du comportement central. Les mutations sont réellement appliquées
# (Produit, SyncCentralLog, SyncAppliedKey).

import uuid

import pytest
import requests as requests_lib
from urllib.parse import urlparse
from sqlalchemy import func

from app import db
from app.models.produit import Produit
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app.models.sync_replica import (
    SyncCursor, SyncOutbox, SyncCentralLog, SyncAppliedKey,
)
from app.security.auth import hash_password, create_access_token_for_user
from app.services.replication import SUPPRESS_OUTBOX_KEY


class _FakeResp:
    """Réponse requests minimaliste (ok + json()) moulée sur une réponse test_client."""

    def __init__(self, resp):
        self._resp = resp
        self.ok = resp.status_code < 400

    def json(self):
        return self._resp.get_json()


class _CentralAdapter:
    """Acheminait `requests.post/get` vers le test_client de l'app (central réel)."""

    def __init__(self, client, headers):
        self._client = client
        self._headers = dict(headers)

    def post(self, url, json=None, **kwargs):
        path = urlparse(url).path
        r = self._client.post(path, json=json, headers=self._headers)
        return _FakeResp(r)

    def get(self, url, params=None, **kwargs):
        path = urlparse(url).path
        r = self._client.get(path, query_string=params, headers=self._headers)
        return _FakeResp(r)


@pytest.fixture
def repl_environment(app, monkeypatch):
    """Met en place un central réel : tenant + utilisateur + JWT de service.

    Monte REPLICATION_URL / REPLICATION_DEVICE_ID / repl_token sur l'app
    locale et redirige `requests` vers les endpoints centraux réels, afin que
    push_pending / pull_changes parcourent le vrai chemin HTTP.
    """
    with app.app_context():
        tenant = Tenant.query.filter_by(slug='cycle-tenant').first()
        if tenant is None:
            tenant = Tenant(
                nom='Tenant Cycle',
                slug='cycle-tenant',
                domaine='cycle.local',
                statut=StatutTenant.ACTIF,
                plan='pro',
            )
            db.session.add(tenant)
            db.session.commit()

        user = Utilisateur.query.filter_by(username='cycleuser').first()
        if user is None:
            user = Utilisateur(
                username='cycleuser',
                email='cycle@test.local',
                password_hash=hash_password('cycle123'),
                role=Role.ADMIN,
                tenant_id=tenant.id,
            )
            db.session.add(user)
            db.session.commit()
        else:
            user.tenant_id = tenant.id
            db.session.commit()
        token = create_access_token_for_user(user)
        tenant_id = tenant.id

    prev_url = app.config.get('REPLICATION_URL')
    prev_device = app.config.get('REPLICATION_DEVICE_ID')
    prev_token = app.extensions.get('repl_token')
    prev_local_tenant = app.config.get('LOCAL_TENANT_ID')

    app.config['REPLICATION_URL'] = 'http://central.test'
    app.config['REPLICATION_DEVICE_ID'] = 'cycle-device'
    app.config['LOCAL_TENANT_ID'] = tenant_id
    app.extensions['repl_token'] = token

    # Simule la production : le serveur CENTRAL ne capture jamais l'outbox.
    # Le hook X-Suppress-Outbox est enregistré au niveau de la fixture `app`
    # (conftest), avant toute première requête.

    adapter = _CentralAdapter(app.test_client(), {
        'Authorization': f'Bearer {token}',
        'X-Device-Id': 'cycle-device',
        'X-Suppress-Outbox': '1',
    })
    monkeypatch.setattr(requests_lib, 'post', adapter.post)
    monkeypatch.setattr(requests_lib, 'get', adapter.get)

    yield {'tenant_id': tenant_id}

    app.config['REPLICATION_URL'] = prev_url
    app.config['REPLICATION_DEVICE_ID'] = prev_device
    if prev_local_tenant is None:
        app.config.pop('LOCAL_TENANT_ID', None)
    else:
        app.config['LOCAL_TENANT_ID'] = prev_local_tenant
    if prev_token is None:
        app.extensions.pop('repl_token', None)
    else:
        app.extensions['repl_token'] = prev_token


def test_full_offline_cycle(app, repl_environment):
    """pull -> mutation locale -> push -> re-push : une seule ligne centrale."""
    from app.services.replication.pull import pull_changes
    from app.services.replication.push import push_pending

    tenant_id = repl_environment['tenant_id']

    # 1. Initialiser le curseur local + une donnée « déjà présente sur le
    #    central » (produit + entrée du journal central) à tirer.
    #    Ce seed ne doit PAS être capturé par l'outbox (ce n'est pas une
    #    mutation utilisateur) : on neutralise la capture pendant l'écriture.
    with app.app_context():
        db.session.info[SUPPRESS_OUTBOX_KEY] = True
        SyncCursor.upsert(
            tenant_id=tenant_id, device_id='cycle-device',
            entity='produit', last_pulled_revision=0,
        )
        p = Produit(
            tenant_id=tenant_id, nom='Ciment 42.5',
            prix_vente_ht=25000, reference='REF-CYCLE-INIT',
        )
        db.session.add(p)
        db.session.flush()
        max_rev = db.session.query(func.max(SyncCentralLog.revision)).scalar() or 0
        db.session.add(SyncCentralLog(
            tenant_id=tenant_id, entity='produit', entity_pk=p.id,
            op='INSERT',
            payload={'nom': 'Ciment 42.5', 'prix_vente_ht': 25000,
                     'reference': 'REF-CYCLE-INIT'},
            revision=max_rev + 1,
        ))
        db.session.commit()
        db.session.info.pop(SUPPRESS_OUTBOX_KEY, None)

    # 2. Pull initial : le curseur avance grâce aux révisions réelles du central.
    report_pull = pull_changes(app)
    assert report_pull['applied'] >= 1
    with app.app_context():
        cur = SyncCursor.query.filter_by(
            tenant_id=tenant_id, device_id='cycle-device', entity='produit'
        ).one()
        assert cur.last_pulled_revision >= 1

    # 3. Mutation locale hors-ligne (nouveau produit créé sur le poste).
    local_uuid = str(uuid.uuid4())
    with app.app_context():
        SyncOutbox.record(
            tenant_id, 'cycle-device', 'produit', 'INSERT',
            {'nom': 'Grave 0/31.5', 'prix_vente_ht': 45000,
             'reference': f'REF-GRAVE-{local_uuid[:8]}'},
            local_uuid, entity_pk=None,
        )

    # 4. Push : le central applique réellement la mutation.
    report_push = push_pending(app)
    assert report_push['sent'] == 1

    # 5. Re-push (retour réseau simulant un acquittement perdu) : le central
    #    répond « duplicate » et NE crée PAS de seconde ligne.
    with app.app_context():
        e = SyncOutbox.query.filter_by(local_uuid=local_uuid).one()
        idempotency_key = e.idempotency_key
        e.status = 'pending'
        db.session.commit()

    report_push2 = push_pending(app)
    assert report_push2['sent'] == 1  # duplicate est compté comme envoyé

    with app.app_context():
        # Une seule ligne « Grave 0/31.5 » côté central (idempotence critique).
        grave = Produit.query.filter_by(
            tenant_id=tenant_id, nom='Grave 0/31.5'
        ).count()
        assert grave == 1
        assert SyncAppliedKey.query.filter_by(
            idempotency_key=idempotency_key
        ).count() == 1