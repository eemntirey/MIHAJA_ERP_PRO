from app import create_app, db
from app.models.tenant import Tenant
from app.models.utilisateur import Utilisateur

app = create_app()

with app.app_context():

    # 1. Créer le tenant
    tenant = Tenant.query.first()

    if tenant is None:
        tenant = Tenant(
            nom="ERP Commercial",
            slug="erp-commercial",
            is_active=True
        )

        db.session.add(tenant)
        db.session.flush()

        print(f"Tenant créé : ID={tenant.id}")
    else:
        print(f"Tenant existant : ID={tenant.id}")

    # 2. Associer tous les utilisateurs au tenant
    utilisateurs = Utilisateur.query.all()

    for utilisateur in utilisateurs:
        utilisateur.tenant_id = tenant.id
        print(
            f"{utilisateur.email} -> tenant_id={tenant.id}"
        )

    db.session.commit()

    print("\nInitialisation multi-tenant terminée.")