"""
MIHAJA_ERP_PRO — Database initialization

OFFICIAL PRODUCTION PATH:
    1. alembic upgrade head   (or: flask db upgrade)
    2. python seed_demo.py    (or other seed scripts)
    3. flask run

This script prefers Alembic. db.create_all() is refused in production.
"""

import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app import db

app = create_app()


def run_alembic_upgrade():
    """Run flask db upgrade. Returns True on success."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "flask", "db", "upgrade"],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
            env={**os.environ, "FLASK_APP": "app:create_app"},
        )
        if result.returncode == 0:
            print("Alembic / Flask-Migrate upgrade successful.")
            if result.stdout.strip():
                print(result.stdout)
            return True
        print("Flask-Migrate upgrade failed:")
        print(result.stderr or result.stdout)
        return False
    except Exception as e:
        print(f"Could not run Flask-Migrate: {e}")
        return False


with app.app_context():
    print("=== Schema migration ===")
    alembic_ok = run_alembic_upgrade()

    if not alembic_ok:
        flask_env = os.getenv("FLASK_ENV", "development").lower()
        if flask_env in ("production", "prod"):
            print(
                "ERROR: Alembic upgrade failed and FLASK_ENV=production. "
                "Refusing to use db.create_all() in production."
            )
            sys.exit(1)
        print(
            "WARNING: Alembic not available or failed. "
            "Falling back to db.create_all() (development only)."
        )
        db.create_all()
        print("Database tables created with db.create_all() (DEV ONLY).")

    print("\n=== Data initialization (subscriptions) ===")
    from app.models.tenant import Tenant
    from app.models.abonnement import Abonnement, StatutAbonnement
    from app.security.plans import apply_plan_to_abonnement
    from datetime import datetime, timedelta

    tenants = Tenant.query.all()
    print(f"Found {len(tenants)} tenants")

    for tenant in tenants:
        print(f"\nTenant: {tenant.nom} (plan: {tenant.plan})")
        abonnement = (
            Abonnement.query.filter_by(tenant_id=tenant.id)
            .order_by(Abonnement.created_at.desc())
            .first()
        )
        if abonnement:
            print(
                f"  Abonnement found: ID={abonnement.id}, "
                f"statut={abonnement.statut.value}, date_fin={abonnement.date_fin}"
            )
            abonnement.statut = StatutAbonnement.ACTIF
            abonnement.date_debut = datetime.utcnow()
            abonnement.date_fin = datetime.utcnow() + timedelta(days=365)
            abonnement.is_active = True
            apply_plan_to_abonnement(abonnement, tenant.plan)
            print(f"  -> Updated: statut=ACTIF, date_fin={abonnement.date_fin}")
        else:
            print("  No subscription found, creating a new one...")
            abonnement = Abonnement(
                tenant_id=tenant.id,
                montant=79.0,
                devise="MGA",
                date_debut=datetime.utcnow(),
                date_fin=datetime.utcnow() + timedelta(days=365),
                statut=StatutAbonnement.ACTIF,
                methode_paiement="especes",
                reference_paiement="SUB-FIX-001",
                plan=tenant.plan or "pro",
            )
            apply_plan_to_abonnement(abonnement, tenant.plan or "pro")
            db.session.add(abonnement)
            print(f"  -> Created: statut=ACTIF")

    db.session.commit()
    print("\nAll subscriptions updated successfully.")
    print("Official production schema path: alembic upgrade head / flask db upgrade")
