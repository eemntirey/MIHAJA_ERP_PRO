from sqlalchemy import text


def reset_schema(database) -> None:
    """Drop & recreate the ``public`` schema to bypass circular FK cycles.

    SQLAlchemy's ``MetaData.drop_all`` cannot resolve circular ForeignKey
    dependencies in the production schema (tenants <-> utilisateurs,
    livreurs <-> vehicules, utilisateurs <-> roles, plus self-references on
    utilisateurs.created_by/updated_by). Using raw ``DROP SCHEMA ... CASCADE``
    avoids the topological sort entirely.

    Les types ENUM créés par SQLAlchemy (via ``CREATE TYPE`` lors de
    ``create_all()``) sont supprimés dynamiquement (requête sur pg_type) au
    lieu d'une liste codée en dur : toute nouvelle colonne ENUM est ainsi
    couverte, et les conflits ``pg_type_typname_nsp_index`` (type orphelin
    réapparu après un OID de schéma réutilisé) sont éliminés. Le pool de
    connexions est ensuite disposé afin qu'aucune connexion ne conserve un
    snapshot ou un statement préparé référencant l'ancien schéma (cause de
    404 ``Abonnement non trouve`` en fin de suite). Si le drop échoue parce
    qu'un objet est verrouillé, on dispose alors le pool et on réessaie.
    """
    def _do_drop():
        engine = database.engine
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
            conn.execute(text('CREATE SCHEMA IF NOT EXISTS public'))
            conn.execute(text('GRANT ALL ON SCHEMA public TO postgres'))
            conn.execute(text('GRANT ALL ON SCHEMA public TO public'))
            # Suppression dynamique de TOUS les types ENUM restants rattachés
            # au schéma public (DROP SCHEMA CASCADE peut laisser des orphelins
            # si l'OID du schéma a été réutilisé).
            enum_types = conn.execute(text(
                "SELECT t.typname FROM pg_type t "
                "JOIN pg_namespace n ON n.oid = t.typnamespace "
                "WHERE n.nspname = 'public' AND t.typtype = 'e'"
            )).fetchall()
            for (type_name,) in enum_types:
                conn.execute(text(f'DROP TYPE IF EXISTS "{type_name}" CASCADE'))
        # Purge du pool : les connexions en cache peuvent porter un snapshot
        # ou des statements préparés liés à l'ancien schéma (OID différent).
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