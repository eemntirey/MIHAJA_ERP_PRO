from sqlalchemy import text, event
import os


def test_database_url() -> str:
    """URL de la base de test, respectant l'environnement.

    Priorité : TEST_DATABASE_URL > DATABASE_URL > défaut local 55432.
    Le nom de base est normalisé sur ``erp_test``.
    """
    _base = (os.getenv('TEST_DATABASE_URL')
             or os.getenv('DATABASE_URL')
             or 'postgresql+psycopg://postgres:postgres@localhost:55432/erp_test')
    return _base.rsplit('/', 1)[0] + '/erp_test'


def reset_schema(database) -> None:
    """Réinitialise le schéma de test (PostgreSQL ou SQLite local).

    SQLAlchemy's ``MetaData.drop_all`` cannot resolve circular ForeignKey
    dependencies in the production schema (tenants <-> utilisateurs,
    livreurs <-> vehicules, utilisateurs <-> roles, plus self-references on
    utilisateurs.created_by/updated_by). Using raw ``DROP SCHEMA ... CASCADE``
    avoids the topological sort entirely.

    Steps:
    1. Kill zombie connections that could hold locks on the schema.
    2. DROP SCHEMA public CASCADE + recreate.
    3. Drop orphaned ENUM types across ALL namespaces (not just ``public``).
    4. Dispose the connection pool so stale connections are not reused.

    Note : pour SQLite (mode local-embedded), le schéma public n'existe pas
    — on utilise ``drop_all()`` avec désactivation temporaire des contraintes
    FK. Cela contourne le problème des cycles de dépendances.
    """
    dialect = database.engine.dialect.name
    if dialect == 'sqlite':
        _reset_sqlite(database)
    else:
        _reset_postgresql(database)


def _reset_sqlite(database) -> None:
    """Réinitialise une base SQLite locale (mode local-embedded)."""
    try:
        database.session.remove()
    except Exception:
        pass

    # Désactiver les contraintes FK pendant le drop_all pour contourner
    # les cycles (tenants <-> utilisateurs, utilisateurs <-> roles, etc.).
    @event.listens_for(database.engine, "before_cursor_execute")
    def _disable_fk_on_drop(conn, cursor, statement, parameters, context, orphans):
        if statement.startswith("DROP"):
            cursor.execute("PRAGMA foreign_keys=OFF")

    try:
        with database.engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
            database.metadata.drop_all(bind=conn)
            conn.execute(text("PRAGMA foreign_keys=ON"))
    finally:
        event.remove(database.engine, "before_cursor_execute", _disable_fk_on_drop)

    database.engine.dispose()


def _reset_postgresql(database) -> None:
    """Réinitialise une base PostgreSQL (central ou tests CI)."""
    def _do_drop():
        engine = database.engine
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            # 1. Tuer uniquement les connexions qui peuvent verrouiller le
            #    schéma (requête en cours, transaction ouverte). On NE touche
            #    PAS aux connexions "idle" du pool : à plusieurs applications
            #    de test (app session + app locales), les tuer provoquait
            #    "server closed the connection" sur les tests suivants.
            conn.execute(text(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = current_database() "
                "AND pid <> pg_backend_pid() "
                "AND state NOT IN ('idle')"
            ))

            # 2. Drop and recreate the public schema.
            conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
            conn.execute(text('CREATE SCHEMA IF NOT EXISTS public'))
            conn.execute(text('GRANT ALL ON SCHEMA public TO postgres'))
            conn.execute(text('GRANT ALL ON SCHEMA public TO public'))

            # 3. Drop ALL orphaned ENUM types (across every namespace, not
            #    just ``public``).  After DROP SCHEMA CASCADE, SQLAlchemy
            #    ENUM types can become orphaned in non-public namespaces
            #    (pg_type still has them, but pg_namespace OID changed).
            #    create_all() would then fail with "duplicate key" on
            #    pg_type_typname_nsp_index.
            orphaned = conn.execute(text(
                "SELECT t.typname, n.nspname "
                "FROM pg_type t "
                "JOIN pg_namespace n ON n.oid = t.typnamespace "
                "WHERE t.typtype = 'e' "
                "AND n.nspname NOT IN ('pg_catalog', 'information_schema')"
            )).fetchall()
            for (type_name, nspname) in orphaned:
                conn.execute(text(
                    f'DROP TYPE IF EXISTS "{nspname}"."{type_name}" CASCADE'
                ))

        # 4. Purge the connection pool.
        try:
            database.session.remove()
        except Exception:
            pass
        engine.dispose()

    try:
        _do_drop()
    except Exception:
        try:
            database.session.remove()
        except Exception:
            pass
        try:
            database.engine.dispose()
        except Exception:
            pass
        _do_drop()
