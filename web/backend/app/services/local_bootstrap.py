# web/backend/app/services/local_bootstrap.py
# Bootstrap idempotent de la base locale embarquée (FLASK_ENV=local-embedded).
import importlib
from sqlalchemy import inspect as sa_inspect


def ensure_local_db_ready(app):
    with app.app_context():
        from app import db
        from flask_migrate import stamp
        # Importer explicitement tous les modèles pour que db.create_all()
        # crée l'intégralité du schéma (y compris tenants, utilisateurs,
        # abonnements, etc.).
        from app import models  # si module modèle global
        # Import explicite des modules modèles connus
        import app.models.tenant
        import app.models.utilisateur
        import app.models.role_permission
        import app.models.abonnement
        import app.models.produit
        import app.models.client
        import app.models.vente
        import app.models.facture
        import app.models.sync_replica
        # Créer toutes les tables si la table alembic_version est absente
        # ou si des tables requises sont manquantes.
        tables = sa_inspect(db.engine).get_table_names()
        required = ('tenants', 'utilisateurs', 'roles', 'permissions', 'abonnements',
                    'produits', 'clients', 'ventes', 'factures')
        missing = [t for t in required if t not in tables]
        if missing or 'alembic_version' not in tables:
            db.create_all()
            stamp(revision='head')
        # Seed des rôles/permissions (idempotent)
        try:
            from scripts.seed_roles import seed_roles
            seed_roles()
        except Exception:
            pass
