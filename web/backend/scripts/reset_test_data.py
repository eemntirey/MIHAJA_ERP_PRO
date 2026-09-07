import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.utilisateur import Utilisateur
from app.models.tenant import Tenant
from app.models.abonnement import Abonnement
from app.models.paiement import Paiement
from app.models.produit import Produit

app = create_app()

from scripts.seed_test_users import main as seed_main

TEST_SLUGS = [
    'distrifood-entreprise',
    'epicerie-solidaire-enterprise',
    'grosriz-distribution',
    'wholesale-center',
    'grossiste-btp',
]

TEST_EMAILS = [
    'distrifood@erp.com',
    'epicerie@erp.com',
    'grosriz@erp.com',
    'wholesale@erp.com',
    'grossiste-btp@erp.com',
    'client.simple@erp.com',
    'client.pub@erp.com',
]


def purge():
    tenants = Tenant.query.filter(Tenant.slug.in_(TEST_SLUGS)).all()
    tenant_ids = [t.id for t in tenants]

    if tenant_ids:
        Paiement.query.filter(Paiement.tenant_id.in_(tenant_ids)).delete(
            synchronize_session=False
        )
        Abonnement.query.filter(Abonnement.tenant_id.in_(tenant_ids)).delete(
            synchronize_session=False
        )
        Produit.query.filter(Produit.tenant_id.in_(tenant_ids)).delete(
            synchronize_session=False
        )
        Utilisateur.query.filter(Utilisateur.tenant_id.in_(tenant_ids)).delete(
            synchronize_session=False
        )
        for t in tenants:
            db.session.delete(t)

    Utilisateur.query.filter(Utilisateur.email.in_(TEST_EMAILS)).delete(
        synchronize_session=False
    )

    db.session.commit()
    print(f"Purge terminee: {len(tenants)} tenants, {len(TEST_EMAILS)} emails test supprimes.")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        purge()
        seed_main()
