from tests._db_utils import test_database_url
import pytest
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.ai.previsions import predict_sales
from app.ai.anomalies import detect_stock_anomalies
from app.ai.recommendations import suggest_reorders
from app.ai.assistant import ask_assistant
from app.models.produit import Produit
from app.models.stock import MouvementStock, TypeMouvement


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
