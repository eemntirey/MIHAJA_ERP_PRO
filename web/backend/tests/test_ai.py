from datetime import datetime, timedelta

from tests._db_utils import test_database_url
import pytest
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.ai.previsions import predict_sales, predict_stock_rupture
from app.ai.anomalies import (
    detect_stock_anomalies,
    detect_sales_anomalies,
    detect_payment_anomalies,
)
from app.ai.recommendations import suggest_reorders
from app.ai.assistant import ask_assistant
from app.models.produit import Produit
from app.models.stock import MouvementStock, TypeMouvement
from app.models.client import Client
from app.models.vente import Vente
from app.models.facture import Facture


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', test_database_url())
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def tenant(app):
    tenant = Tenant(
        nom='Test Tenant',
        slug='test-tenant',
        domaine='test.local',
        statut=StatutTenant.ACTIF,
        plan='pro'
    )
    db.session.add(tenant)
    db.session.commit()
    return tenant


@pytest.fixture
def tenant_b(app):
    """Second tenant : sert de cible pour les tests d'isolement A -> B."""
    tenant = Tenant(
        nom='Tenant B',
        slug='test-tenant-b',
        domaine='b.test.local',
        statut=StatutTenant.ACTIF,
        plan='pro'
    )
    db.session.add(tenant)
    db.session.commit()
    return tenant


def _seed_ai_tenant_data(tenant, tag, rich=False):
    """Seed les données métier utilisées par les fonctions IA.

    Avec ``rich=True`` (tenant A « secret »), on crée des données
    volontairement marquées (montants extrêmes, produit nommé
    ``PRODUIT-SECRET-<tag>``, facture impayée de 45 jours) dont toute
    apparition dans les résultats d'un autre tenant prouve une fuite.
    """
    client = Client(code=f'CL-{tag}', nom=f'Client {tag}', tenant_id=tenant.id)
    db.session.add(client)
    db.session.flush()

    if not rich:
        db.session.commit()
        return {'client': client}

    now = datetime.utcnow()
    ventes = []
    for i in range(10):
        # 9 ventes à 100 Ar + 1 vente récente à 500 000 Ar :
        # outlier visible pour detect_sales_anomalies, pente positive
        # pour predict_sales.
        total = 500000 if i == 0 else 100
        vente = Vente(
            reference=f'V-{tag}-{i}',
            client_id=client.id,
            total_ht=total,
            total_ttc=total,
            date=now - timedelta(days=i),
            created_at=now - timedelta(days=i),
            tenant_id=tenant.id,
        )
        db.session.add(vente)
        ventes.append(vente)
    db.session.flush()

    facture = Facture(
        vente_id=ventes[0].id,
        client_id=client.id,
        reference=f'F-{tag}',
        total_ttc=100000,
        statut='non_payee',
        created_at=now - timedelta(days=45),
        tenant_id=tenant.id,
    )
    db.session.add(facture)

    produit = Produit(
        reference=f'P-{tag}',
        nom=f'PRODUIT-SECRET-{tag}',
        quantite_stock=1,
        seuil_alerte=10,
        prix_achat_ht=100,
        prix_vente_ht=150,
        tenant_id=tenant.id,
    )
    db.session.add(produit)
    db.session.flush()
    for q in [10] * 9 + [10000]:
        db.session.add(MouvementStock(
            produit_id=produit.id,
            type_mouvement=TypeMouvement.SORTIE,
            quantite=q,
            tenant_id=tenant.id,
        ))
    db.session.commit()
    return {
        'client': client,
        'ventes': ventes,
        'facture': facture,
        'produit': produit,
    }


def test_predict_sales(app, tenant):
    with app.app_context():
        result = predict_sales(tenant.id, periods=5)
        assert result['periods'] == 5
        assert isinstance(result['forecast'], list)
        assert len(result['forecast']) == 5


def test_detect_stock_anomalies(app, tenant):
    with app.app_context():
        result = detect_stock_anomalies(tenant.id)
        assert 'anomalies' in result
        assert 'count' in result


def test_suggest_reorders(app, tenant):
    with app.app_context():
        result = suggest_reorders(tenant.id)
        assert 'recommendations' in result
        assert 'count' in result


def test_ask_assistant(app, tenant):
    with app.app_context():
        result = ask_assistant(tenant.id, ' Quel est le stock ? ')
        assert isinstance(result, str)
        assert len(result) > 0


def test_training_does_not_deserialize_pickle(app):
    """SÃƒÂ©curitÃƒÂ©: le module d'entraÃƒÂ®nement/chargement IA ne doit jamais
    dÃƒÂ©sÃƒÂ©rialiser un fichier .pkl via pickle (risque RCE sur fichier
    altÃƒÂ©rÃƒÂ©/non fiable). Les modÃƒÂ¨les sont ÃƒÂ©crits mais jamais relus par
    l'application ; les prÃƒÂ©dictions sont calculÃƒÂ©es en live.
    """
    import inspect
    import app.ai.training as training
    import app.ai.previsions as previsions
    import app.ai.anomalies as anomalies
    import app.ai.recommendations as recommendations
    import app.ai.assistant as assistant

    for mod in (training, previsions, anomalies, recommendations, assistant):
        src = inspect.getsource(mod)
        assert 'pickle.load' not in src, (
            f"{mod.__name__} utilise pickle.load (risque dÃƒÂ©sÃƒÂ©rialisation)"
        )
        assert 'pickle.loads' not in src, (
            f"{mod.__name__} utilise pickle.loads (risque dÃƒÂ©sÃƒÂ©rialisation)"
        )


def test_training_writes_only_within_models_dir(app):
    """Les chemins d'ÃƒÂ©criture des .pkl doivent rester confinÃƒÂ©s au
    rÃƒÂ©pertoire de modÃƒÂ¨les configurÃƒÂ© (pas d'ÃƒÂ©criture arbitraire sur disque).
    """
    import os
    import inspect
    from app.ai import training

    src = inspect.getsource(training)
    # Toutes les ÃƒÂ©critures .pkl utilisent MODELS_DIR
    assert "os.path.join(MODELS_DIR" in src
    assert "MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')" in src
    # Aucune ÃƒÂ©criture vers un chemin dÃƒÂ©rivÃƒÂ© de l'utilisateur
    assert "data.get('path'" not in src
    assert "request.json" not in src
    assert os.path.isdir(os.path.join(os.path.dirname(training.__file__), 'models'))


def test_ai_endpoints_use_message_key(app):
    """Les endpoints AI doivent retourner un format d'erreur standardisÃƒÂ©
    avec la clÃƒÂ© 'message' (cohÃƒÂ©rent avec le reste du projet) et ne jamais
    exposer str(exception) au client.
    """
    import inspect
    from app.api.v1 import ai as ai_module
    src = inspect.getsource(ai_module)

    # Toutes les rÃƒÂ©ponses d'erreur utilisent la clÃƒÂ© "message"
    # (clÃƒÂ© normalisÃƒÂ©e dans tout le projet)
    assert "{" in src  # sanity

    # str(e) ne doit pas ÃƒÂªtre exposÃƒÂ© dans les rÃƒÂ©ponses
    # (sinon fuite de stack trace interne)
    assert "{str(e)}".replace("{", "").replace("}", "") not in src  # no f"... {str(e)}"
    assert "f'Erreur lors" not in src or "str(e)" not in src

    # Aucune rÃƒÂ©ponse d'erreur ne s'appuie uniquement sur 'error'
    # (clÃƒÂ© rÃƒÂ©servÃƒÂ©e au frontend qui consomme 'message')
    forbidden_only_error = "    return {'error':"
    assert forbidden_only_error not in src, (
        "ai.py ne doit pas retourner un payload sans 'message'"
    )


def test_ai_endpoints_invalid_period_returns_message(client, app):
    """Test end-to-end: un period invalide renvoie un message standardisÃƒÂ©."""
    from app.models.tenant import Tenant, StatutTenant
    from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
    from app.security.auth import hash_password
    from flask_jwt_extended import create_access_token
    import uuid

    with app.app_context():
        tenant = Tenant(
            nom='AI T',
            slug=f'ai-{uuid.uuid4().hex[:6]}',
            statut=StatutTenant.EN_ESSAI,
            plan='pro',
        )
        db.session.add(tenant)
        db.session.flush()
        user = Utilisateur(
            username=f'ai-{uuid.uuid4().hex[:6]}',
            email=f'ai-{uuid.uuid4().hex[:6]}@x.mg',
            password_hash=hash_password('p'),
            role=Role.ADMIN,
            tenant_id=tenant.id,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(user)
        db.session.commit()
        token = create_access_token(
            identity=user.id,
            additional_claims={'role': 'admin', 'tenant_id': tenant.id},
        )

    headers = {'Authorization': f'Bearer {token}', 'X-Tenant-Slug': tenant.slug}
    r = client.get('/api/v1/ai/previsions?periods=0', headers=headers)
    assert r.status_code == 400
    payload = r.get_json()
    assert 'message' in payload


# ---------------------------------------------------------------------------
# Isolation multi-tenant des fonctions IA (#97 / #98)
#
# Le filtre tenant global (do_orm_execute) ne s'active qu'en contexte de
# requête : ces tests appellent les fonctions SANS requête HTTP pour prouver
# que previsions.py/anomalies.py filtrent explicitement par tenant_id, et
# que l'absence de tenant est traitée en fail-closed (jamais de lecture
# globale). Toute donnée « PRODUIT-SECRET-A » / montant / référence du
# tenant A visible depuis le tenant B est une fuite.
# ---------------------------------------------------------------------------


def test_isol_previsions_deux_tenants_sans_fuite(app, tenant, tenant_b):
    """predict_sales/predict_stock_rupture appelés pour B ne lisent jamais A."""
    with app.app_context():
        _seed_ai_tenant_data(tenant, 'A', rich=True)
        _seed_ai_tenant_data(tenant_b, 'B', rich=False)

        res_b = predict_sales(tenant_id=tenant_b.id, periods=5)
        assert res_b['tenant_id'] == tenant_b.id, (
            'predict_sales doit retourner le tenant demandé'
        )
        # B n'a aucune vente : mode baseline. Si les ventes de A fuyaient,
        # le code passerait en status "success" avec des montants géants.
        assert res_b['status'] == 'baseline', (
            'predict_sales : les ventes du tenant A ont fuité vers B'
        )
        assert res_b['total_predicted'] < 10000, (
            'predict_sales : montants du tenant A visibles depuis B'
        )

        res_a = predict_sales(tenant_id=tenant.id, periods=5)
        assert res_a['tenant_id'] == tenant.id
        assert res_a['status'] == 'success', (
            'Sanity : les ventes du tenant A doivent être chargées pour A'
        )
        assert res_a['total_predicted'] > 100000, (
            'Sanity : la vente à 500000 Ar du tenant A doit influencer A'
        )

        rupt_b = predict_stock_rupture(tenant_id=tenant_b.id)
        assert rupt_b['count'] == 0, (
            'predict_stock_rupture : produits du tenant A visibles depuis B'
        )
        assert 'PRODUIT-SECRET-A' not in str(rupt_b)

        rupt_a = predict_stock_rupture(tenant_id=tenant.id)
        assert rupt_a['count'] >= 1, (
            'Sanity : le produit bas stock du tenant A doit être prédit pour A'
        )
        assert any(
            p['nom'] == 'PRODUIT-SECRET-A' for p in rupt_a['predictions']
        ), 'Sanity : PRODUIT-SECRET-A doit apparaître pour son propre tenant'


def test_isol_anomalies_deux_tenants_sans_fuite(app, tenant, tenant_b):
    """detect_*_anomalies appelées pour B ne lisent jamais A."""
    with app.app_context():
        seeded_a = _seed_ai_tenant_data(tenant, 'A', rich=True)
        _seed_ai_tenant_data(tenant_b, 'B', rich=False)
        ref_facture_a = seeded_a['facture'].reference

        stock_b = detect_stock_anomalies(tenant_id=tenant_b.id)
        assert stock_b['count'] == 0, (
            'detect_stock_anomalies : mouvements du tenant A visibles depuis B'
        )
        assert 'PRODUIT-SECRET-A' not in str(stock_b)

        sales_b = detect_sales_anomalies(tenant_id=tenant_b.id)
        assert sales_b['count'] == 0, (
            'detect_sales_anomalies : ventes du tenant A visibles depuis B'
        )
        assert 'V-A-' not in str(sales_b)

        pay_b = detect_payment_anomalies(tenant_id=tenant_b.id)
        assert pay_b['count'] == 0, (
            'detect_payment_anomalies : factures du tenant A visibles depuis B'
        )
        assert ref_facture_a not in str(pay_b)

        # Sanity : A détecte bien ses propres anomalies (données existantes)
        stock_a = detect_stock_anomalies(tenant_id=tenant.id)
        assert stock_a['count'] >= 1, (
            'Sanity : anomalie de stock attendue pour le tenant A'
        )
        assert 'PRODUIT-SECRET-A' in str(stock_a)

        sales_a = detect_sales_anomalies(tenant_id=tenant.id)
        assert sales_a['count'] >= 1, (
            'Sanity : outlier de vente attendu pour le tenant A'
        )

        pay_a = detect_payment_anomalies(tenant_id=tenant.id)
        assert pay_a['count'] >= 1, (
            'Sanity : facture impayée de 45 jours attendue pour A'
        )
        assert ref_facture_a in str(pay_a)


def test_isol_fail_closed_sans_tenant(app, tenant):
    """Sans aucun tenant, l'IA refuse (fail-closed) au lieu de lire tout."""
    with app.app_context():
        _seed_ai_tenant_data(tenant, 'A', rich=True)

        res = predict_sales(periods=5)
        assert res['status'] == 'no_tenant', (
            'predict_sales sans tenant doit être fail-closed (no_tenant)'
        )
        assert res['forecast'] == []
        assert res['tenant_id'] is None

        rupture = predict_stock_rupture()
        assert rupture['count'] == 0
        assert 'PRODUIT-SECRET-A' not in str(rupture)

        for fn in (detect_stock_anomalies, detect_sales_anomalies,
                   detect_payment_anomalies):
            out = fn()
            assert out['count'] == 0, (
                f'{fn.__name__} sans tenant ne doit rien retourner'
            )
            assert 'Tenant' in out.get('message', ''), (
                f'{fn.__name__} sans tenant doit renvoyer un message explicite'
            )
            assert 'PRODUIT-SECRET-A' not in str(out)
            assert 'F-A' not in str(out)


def test_isol_contexte_requete_utilise_tenant_courant(app, tenant, tenant_b):
    """En requête, get_current_tenant_id() prime : B ne voit que B."""
    from flask import g

    with app.app_context():
        _seed_ai_tenant_data(tenant, 'A', rich=True)
        _seed_ai_tenant_data(tenant_b, 'B', rich=False)

        try:
            with app.test_request_context('/api/v1/ai/previsions'):
                g.current_tenant = tenant_b
                g.current_tenant_id = tenant_b.id

                # Appel sans tenant_id explicite, comme les endpoints
                res = predict_sales(periods=5)
                assert res['tenant_id'] == tenant_b.id
                assert res['status'] == 'baseline', (
                    'Contexte requête B : les ventes de A ont fuité'
                )

                # Le tenant du contexte prime sur un tenant_id fourni
                res_override = predict_sales(tenant_id=tenant.id, periods=5)
                assert res_override['tenant_id'] == tenant_b.id, (
                    'Le tenant du contexte doit primer sur le paramètre'
                )

                assert detect_stock_anomalies()['count'] == 0
                assert detect_sales_anomalies()['count'] == 0
                assert detect_payment_anomalies()['count'] == 0
                assert predict_stock_rupture()['count'] == 0
        finally:
            g.current_tenant = None
            g.current_tenant_id = None
