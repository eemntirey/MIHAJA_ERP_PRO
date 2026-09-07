"""Utilitaires partagés pour la suite de tests.

`reset_schema` permet de contourner les cycles de dépendances FK qui
empêchent SQLAlchemy de trier proprement les tables lors d'un ``drop_all``.
"""
from sqlalchemy import text


def reset_schema(database) -> None:
    """Drop & recreate the ``public`` schema to bypass circular FK cycles.

    SQLAlchemy's ``MetaData.drop_all`` cannot resolve circular ForeignKey
    dependencies in the production schema (tenants <-> utilisateurs,
    livreurs <-> vehicules, utilisateurs <-> roles, plus self-references on
    utilisateurs.created_by/updated_by). Using raw ``DROP SCHEMA ... CASCADE``
    avoids the topological sort entirely.

    Les types ENUM créés par SQLAlchemy (via ``CREATE TYPE`` lors de
    ``create_all()``) sont également supprimés par le ``CASCADE``. On évite
    de disposer le pool SQLAlchemy local pour ne pas casser les connexions
    ouvertes par d'autres fixtures (ex. ``_db_isolation``). Si le drop
    échoue parce qu'un objet est verrouillé, on dispose alors le pool et on
    réessaie.
    """
    def _do_drop():
        with database.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
            conn.execute(text('CREATE SCHEMA IF NOT EXISTS public'))
            conn.execute(text('GRANT ALL ON SCHEMA public TO postgres'))
            conn.execute(text('GRANT ALL ON SCHEMA public TO public'))
            # DROP SCHEMA CASCADE ne supprime pas toujours les ENUM types
            # (créés via CREATE TYPE) parce qu'ils ne sont pas rattachés à
            # un schéma nommé. On force donc leur suppression explicite.
            for type_name in (
                'role', 'statututilisateur', 'statuttenant', 'statutadmin',
                'statutcommande', 'statutabonnement', 'statutdevice',
                'statutpaiement', 'statutlivraison', 'statutemploye',
                'statutfacture', 'statutpresence', 'statutprime',
                'statutsalaire', 'statutpaiementfournisseur',
                'statutreception', 'statutstagiaire', 'statutdocument',
                'typemouvementstock', 'typefacture', 'typecommande',
                'typepaiement', 'methodepaiement',
            ):
                conn.execute(text(f'DROP TYPE IF EXISTS "{type_name}" CASCADE'))

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