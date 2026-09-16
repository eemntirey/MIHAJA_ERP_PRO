import pytest
from app import create_app
from app.models.platform_config import PlatformConfig
from app import db

@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

def test_toggle_cree_et_lit(app):
    with app.test_client() as client:
        # Authentifier comme super admin (simulé par un token valide serait nécessaire)
        # Pour ce test rapide, on vérifie le modèle directement
        cfg = PlatformConfig.get_config()
        assert cfg.is_subscription_active is False
        cfg.is_subscription_active = True
        db.session.commit()
        cfg2 = PlatformConfig.get_config()
        assert cfg2.is_subscription_active is True
