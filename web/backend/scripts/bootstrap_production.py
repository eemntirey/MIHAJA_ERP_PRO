#!/usr/bin/env python3
"""Bootstrap strict d'une base PostgreSQL MIHAJA ERP neuve.

Ce script est volontairement distinct de `flask db upgrade` :
V0 possede une baseline historique vide et des migrations incrementales qui
supposent qu'un schema de base existe deja. Pour une base PostgreSQL totalement
neuve, on construit donc le schema courant via SQLAlchemy, puis on enregistre
explicitement la revision V0 correspondante.

SECURITE :
- PostgreSQL uniquement.
- Refuse une base deja partiellement initialisee.
- Ne fait jamais drop_all().
- Ne purge jamais alembic_version.
- Ne lance jamais stamp avant d'avoir verifie le schema.
- Idempotent uniquement apres une initialisation complete a la revision attendue.
"""

import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
os.chdir(_BACKEND_ROOT)
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

EXPECTED_HEAD = "z9y8x7w6v5u4"
REQUIRED_TABLES = {"tenants", "utilisateurs", "roles", "permissions"}


def fail(message):
    print(f"ERREUR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main():
    from sqlalchemy import inspect, text
    from app import create_app, db
    from flask_migrate import stamp
    from scripts.seed_roles import seed_roles
    from scripts.create_superadmin import create_super_admin

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        fail("DATABASE_URL est obligatoire.")

    if database_url.lower().startswith("sqlite"):
        fail("SQLite est interdit pour ce bootstrap de production.")

    if "postgresql" not in database_url.lower():
        fail("DATABASE_URL doit cibler PostgreSQL.")

    email = os.getenv("SUPERADMIN_EMAIL", "superadmin@mihaja.mg").strip()
    username = os.getenv("SUPERADMIN_USERNAME", "superadmin").strip()
    password = os.getenv("SUPERADMIN_PASSWORD", "").strip()
    if not password:
        fail("SUPERADMIN_PASSWORD est obligatoire pour creer le Super Admin.")

    app = create_app()

    with app.app_context():
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        user_tables = tables - {"alembic_version"}

        # Etat deja initialise proprement : on ne recree rien.
        if user_tables:
            missing = REQUIRED_TABLES - tables
            if missing:
                fail(
                    "base partiellement initialisee; tables obligatoires absentes: "
                    + ", ".join(sorted(missing))
                    + ". Aucune modification effectuee."
                )

            version_rows = []
            if "alembic_version" in tables:
                version_rows = [
                    row[0]
                    for row in db.session.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).all()
                ]

            if version_rows == [EXPECTED_HEAD]:
                seed_roles(app)
                create_super_admin(
                    email=email,
                    username=username,
                    password=password,
                    force=False,
                )
                print("OK: base deja initialisee; roles/permissions et Super Admin verifies.")
                return

            fail(
                "base non vide mais revision Alembic differente de la baseline attendue "
                f"(attendu {EXPECTED_HEAD}). Aucune modification effectuee."
            )

        # Base vide : creation du schema courant.
        print("Base PostgreSQL vide detectee.")
        print("Creation du schema courant via SQLAlchemy...")
        db.create_all()

        inspector = inspect(db.engine)
        tables_after = set(inspector.get_table_names())
        metadata_tables = set(db.metadata.tables.keys())
        missing_required = REQUIRED_TABLES - tables_after
        missing_metadata = metadata_tables - tables_after

        if missing_required:
            fail(
                "db.create_all() n'a pas cree les tables obligatoires: "
                + ", ".join(sorted(missing_required))
            )

        if missing_metadata:
            fail(
                "schema incomplet apres db.create_all(); tables SQLAlchemy absentes: "
                + ", ".join(sorted(missing_metadata))
            )

        print(f"Schema cree: {len(metadata_tables)} tables SQLAlchemy.")

        # V0 est une chaine incrementale construite sur ce schema historique.
        # Sur une base neuve, les migrations historiques ne doivent pas etre
        # rejouees sur un schema deja finalise.
        print(f"Enregistrement de la revision Alembic {EXPECTED_HEAD}...")
        stamp(directory=str(_BACKEND_ROOT / "migrations"), revision=EXPECTED_HEAD)

        version_rows = [
            row[0]
            for row in db.session.execute(
                text("SELECT version_num FROM alembic_version")
            ).all()
        ]
        if version_rows != [EXPECTED_HEAD]:
            fail(
                "verification Alembic echouee: version actuelle = "
                + repr(version_rows)
            )

        print("Seed des roles et permissions...")
        seed_roles(app)

        print("Creation/verif du Super Admin...")
        user, created, changed = create_super_admin(
            email=email,
            username=username,
            password=password,
            force=False,
        )

        if user is None:
            fail("Le Super Admin n'a pas pu etre cree/verifie.")

        final_tables = set(inspect(db.engine).get_table_names())
        missing_final = REQUIRED_TABLES - final_tables
        if missing_final:
            fail(
                "verification finale echouee; tables absentes: "
                + ", ".join(sorted(missing_final))
            )

        print("BOOTSTRAP PRODUCTION OK")
        print(f"  Alembic: {EXPECTED_HEAD}")
        print(f"  Super Admin: {email}")
        print(f"  Compte cree: {created}")
        print(f"  Changements: {', '.join(changed) if changed else 'aucun'}")


if __name__ == "__main__":
    main()
