import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app import db

app = create_app()

with app.app_context():
    # Create all tables
    db.create_all()
    print("Database tables created successfully!")

    # Check if there are any tenants
    from app.models.tenant import Tenant
    from app.models.abonnement import Abonnement, StatutAbonnement
    from app.security.plans import apply_plan_to_abonnement
    from datetime import datetime, timedelta

    tenants = Tenant.query.all()
    print(f"Found {len(tenants)} tenants")

    for tenant in tenants:
        print(f"\nTenant: {tenant.nom} (plan: {tenant.plan})")

        # Get the latest subscription for this tenant
        abonnement = Abonnement.query.filter_by(
            tenant_id=tenant.id
        ).order_by(Abonnement.created_at.desc()).first()

        if abonnement:
            print(f"  Abonnement found: ID={abonnement.id}, statut={abonnement.statut.value}, date_fin={abonnement.date_fin}")

            # Update the subscription to be active
            abonnement.statut = StatutAbonnement.ACTIF
            abonnement.date_debut = datetime.utcnow()
            abonnement.date_fin = datetime.utcnow() + timedelta(days=365)
            abonnement.is_active = True

            # Apply plan configuration (this sets the modules field)
            apply_plan_to_abonnement(abonnement, tenant.plan)

            print(f"  -> Updated: statut=ACTIF, date_fin={abonnement.date_fin}")
            print(f"  -> Modules: {abonnement.modules}")
        else:
            print("  No subscription found, creating a new one...")
            # Create a new subscription
            abonnement = Abonnement(
                tenant_id=tenant.id,
                montant=79.0,
                devise='MGA',
                date_debut=datetime.utcnow(),
                date_fin=datetime.utcnow() + timedelta(days=365),
                statut=StatutAbonnement.ACTIF,
                methode_paiement='especes',
                reference_paiement='SUB-FIX-001',
                plan=tenant.plan or 'pro',
            )
            apply_plan_to_abonnement(abonnement, tenant.plan or 'pro')
            db.session.add(abonnement)
            print(f"  -> Created: statut=ACTIF, date_fin={abonnement.date_fin}")

    db.session.commit()
    print("\nAll subscriptions have been updated successfully!")
