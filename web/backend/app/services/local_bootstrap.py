# web/backend/app/services/local_bootstrap.py
# Bootstrap idempotent de la base locale embarquée (FLASK_ENV=local-embedded).
#
# Appelé au démarrage du backend local (run.py / run_local.py) : première
# installation -> création du schéma + stamp Alembic ; ensuite, no-op.
import datetime
import enum
import logging
import re
from decimal import Decimal

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
    import app.models  # noqa: F401  (importe l'ensemble des modèles métier)
    import app.models.sync_replica  # noqa: F401


def _render_server_default(server_default):
    """Rend un server_default sous forme SQL littérale (SQLite)."""
    arg = server_default.arg
    if hasattr(arg, 'text'):  # sa.text('...')
        return arg.text
    rendered = str(arg).strip()
    if not rendered:
        return ''
    if rendered.upper() in ('TRUE', 'FALSE', 'NULL') or \
            re.fullmatch(r'-?\d+(\.\d+)?', rendered):
        return rendered
    return "'" + rendered.replace("'", "''") + "'"


def _render_value_literal(value):
    """Rend une valeur Python en littéral SQL, ou None si non rendable."""
    if isinstance(value, enum.Enum):
        value = value.value
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if value is None:
        return 'NULL'
    if isinstance(value, (str, datetime.date)):
        # datetime est une sous-classe de date.
        return "'" + str(value).replace("'", "''") + "'"
    return None


def _placeholder_literal(column_type):
    """Placeholder SQL sûr pour une colonne NOT NULL sans défaut rendable."""
    from sqlalchemy import types as sql_types
    if isinstance(column_type, sql_types.Boolean):
        return '0'
    if isinstance(column_type, sql_types.Integer):
        return '0'
    if isinstance(column_type, sql_types.Numeric):
        return '0'
    if isinstance(column_type, sql_types.DateTime):
        return "'1970-01-01 00:00:00'"
    if isinstance(column_type, sql_types.Date):
        return "'1970-01-01'"
    if isinstance(column_type, sql_types.Enum):
        # Enum natif : '' peut être invalide, pas de placeholder sûr.
        return None
    if isinstance(column_type, sql_types.String):
        return "''"
    return None


def _column_default_literal(column):
    """Défaut serveur à utiliser pour ALTER TABLE ADD COLUMN.

    Comble le drift en trois voies modèle/migration/réparation :

    1. `server_default` (modèle ou migration, ex. produits.published = 1) ;
    2. `default` Python du modèle (colonnes déclarées sans server_default,
       ex. produits.stock_min = 0, employes.conges_credit_annuel = 30) ;
    3. placeholder selon le type pour une colonne NOT NULL sans défaut.

    Retourne None si aucun défaut n'est applicable (colonne nullable sans
    défaut, ou type sans placeholder sûr) — l'appelant décide alors.
    """
    if column.server_default is not None:
        return _render_server_default(column.server_default)
    if column.default is not None:
        arg = getattr(column.default, 'arg', column.default)
        if not callable(arg):
            literal = _render_value_literal(arg)
            if literal is not None:
                return literal
    if not column.nullable:
        return _placeholder_literal(column.type)
    return None


def _repair_missing_columns():
    """Ajoute les colonnes des modèles absentes de la base locale.

    Une base locale créée par `create_all` lors d'une version antérieure reste
    marquée Alembic 'head' : les migrations ultérieures ne s'appliquent jamais
    (même pathologie que l'incident central du 2026-09-22 sur instance/erp.db,
    colonnes produits.stock_min / utilisateurs.local_password_hash manquantes).
    SQLite autorise ALTER TABLE ADD COLUMN pour une colonne nullable ou avec
    défaut serveur ; pour une colonne NOT NULL déclarée sans server_default
    (drift modèle/migration, ex. produits.published), le défaut est dérivé du
    `default` Python du modèle puis, à défaut, d'un placeholder de type, afin
    que la réparation ne soit jamais bloquée. Chaque ajout est journalisé et
    n'interrompt jamais le démarrage du poste.
    """
    from app import db
    from sqlalchemy import text

    inspector = sa_inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    dialect = db.engine.dialect
    added = []
    for table in db.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        try:
            existing_cols = {
                col['name'] for col in inspector.get_columns(table.name)
            }
        except Exception:
            continue
        for column in table.columns:
            if column.name in existing_cols:
                continue
            default_literal = _column_default_literal(column)
            if default_literal is None and not column.nullable:
                logger.warning(
                    'Colonne %s.%s non-nullable sans défaut exploitable : '
                    'ajout ignoré (schéma local à reconstruire).',
                    table.name, column.name,
                )
                continue
            try:
                col_type = column.type.compile(dialect=dialect)
                default_sql = ''
                if default_literal is not None:
                    default_sql = ' DEFAULT ' + default_literal
                db.session.execute(text(
                    f'ALTER TABLE {table.name} ADD COLUMN '
                    f'{column.name} {col_type}{default_sql}'
                ))
                db.session.commit()
                added.append(f'{table.name}.{column.name}')
            except Exception:
                db.session.rollback()
                logger.exception(
                    'Ajout impossible de la colonne %s.%s sur la base locale.',
                    table.name, column.name,
                )
    if added:
        logger.warning(
            'Schéma local réparé : colonnes ajoutées -> %s', ', '.join(added)
        )


def ensure_local_db_ready(app):
    """Prépare la base locale : schéma + migration + rôles système.

    Idempotent : peut être appelé à chaque démarrage du poste.
    """
    with app.app_context():
        from app import db
        from flask_migrate import stamp, upgrade

        _import_models()
        tables = sa_inspect(db.engine).get_table_names()

        # create_all est idempotent : il complète une base ancienne incomplète
        # (tables ajoutées dans de nouvelles versions du modèle) et ne touche
        # à rien sur une base à jour.
        db.create_all()

        if 'alembic_version' not in tables:
            # Première installation : le schéma vient d'être créé par
            # create_all, on marque la version pour les migrations futures.
            logger.warning(
                'Base locale embarquée inexistante : création du schéma.'
            )
            stamp(revision='head')
        else:
            # Base existante : applique les migrations éventuellement
            # manquantes (no-op si déjà à la tête).
            try:
                upgrade()
            except Exception:
                # Ne jamais empêcher le poste de démarrer ; la réparation de
                # colonnes ci-dessous couvre déjà le cas le plus fréquent.
                logger.exception(
                    'Échec des migrations Alembic sur la base locale embarquée.'
                )

        _repair_missing_columns()

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
