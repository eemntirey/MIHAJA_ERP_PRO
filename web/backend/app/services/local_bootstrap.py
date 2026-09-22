# web/backend/app/services/local_bootstrap.py
# Bootstrap idempotent de la base locale embarquée (FLASK_ENV=local-embedded).
#
# Appelé au démarrage du backend local (run.py / run_local.py) : première
# installation -> création du schéma + stamp Alembic ; ensuite, no-op.
import logging

from sqlalchemy import inspect as sa_inspect

logger = logging.getLogger(__name__)

# Tables dont l'absence prouve que le schéma local n'a jamais été créé.
_REQUIRED_TABLES = (
    'tenants', 'utilisateurs', 'roles', 'permissions', 'abonnements',
    'produits', 'clients', 'ventes', 'factures', 'sync_outbox',
    'sync_cursors', 'sync_conflicts', 'sync_state', 'sync_local_mappings',
)


def _import_models():
    """Importe tous les modèles pour que `create_all` crée le schéma complet."""
    import app.models.tenant  # noqa: F401
    import app.models.utilisateur  # noqa: F401
    import app.models.role_permission  # noqa: F401
    import app.models.abonnement  # noqa: F401
    import app.models.produit  # noqa: F401
    import app.models.client  # noqa: F401
    import app.models.vente  # noqa: F401
    import app.models.facture  # noqa: F401
    import app.models.fournisseur  # noqa: F401
    import app.models.sync_replica  # noqa: F401


def ensure_local_db_ready(app):
    """Prépare la base locale : schéma + migration + rôles système.

    Idempotent : peut être appelé à chaque démarrage du poste.
    """
    with app.app_context():
        from app import db
        from flask_migrate import stamp

        _import_models()
        tables = sa_inspect(db.engine).get_table_names()
        missing = [t for t in _REQUIRED_TABLES if t not in tables]
        if missing or 'alembic_version' not in tables:
            logger.warning(
                'Base locale embarquée incomplète (%s) : création du schéma.',
                ', '.join(missing) or 'version Alembic absente',
            )
            db.create_all()
            stamp(revision='head')
            tables = sa_inspect(db.engine).get_table_names()

        # Rôles/permissions système (idempotent : ne s'exécute que si vide).
        try:
            from scripts.seed_roles import seed_roles
            seed_roles(app)
        except Exception:
            # Ne jamais empêcher le poste de démarrer : un échec de seed est
            # signalé (le login hors-ligne reste possible).
            logger.exception(
                'Échec du seed des rôles sur la base locale embarquée.'
            )
        return True


def ensure_local_cursors(tenant_id):
    """Prépare les curseurs de réplication du poste (cf. replication.pull).

    Appelé après un login réussi : sans curseur, le poste ne tire jamais les
    données du central.
    """
    from app.services.replication.pull import ensure_cursors
    return ensure_cursors(tenant_id)
