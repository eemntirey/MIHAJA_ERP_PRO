#!/usr/bin/env python3
"""Bootstrap strict d'une base PostgreSQL MIHAJA ERP neuve.

Ce script initialise automatiquement une base PostgreSQL Render totalement
vide, sans shell manuel.

SECURITE :
- PostgreSQL uniquement.
- Base vide uniquement pour la creation initiale.
- Base partielle ou incoherente => arret sans modification.
- Jamais de drop_all(), purge d'alembic_version ou reset de donnees.
- Revision Alembic head determinee depuis les fichiers V0, jamais codee en dur.
- Verrou PostgreSQL pour eviter deux bootstraps concurrents.
"""

import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
os.chdir(_BACKEND_ROOT)
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

REQUIRED_TABLES = {"tenants", "utilisateurs", "roles", "permissions"}
LOCK_KEY = "mihaja_erp_v0_production_bootstrap"


def fail(message):
    print(f"ERREUR: {message}", file=sys.stderr)
    raise SystemExit(1)


def get_migration_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(_BACKEND_ROOT / "migrations" / "alembic.ini"))
    config.set_main_option(
        "script_location", str(_BACKEND_ROOT / "migrations")
    )
    script = ScriptDirectory.from_config(config)
    heads = list(script.get_heads())
    if len(heads) != 1:
        fail(
            "La chaine Alembic V0 doit avoir exactement un head; "
            f"heads detectes: {heads}"
        )
    return heads[0]


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

    expected_head = get_migration_head()
    email = os.getenv("SUPERADMIN_EMAIL", "superadmin@mihaja.mg").strip()
    username = os.getenv("SUPERADMIN_USERNAME", "superadmin").strip()

    app = create_app()

    with app.app_context():
        # Verrou session PostgreSQL : deux instances ne peuvent pas initialiser
        # simultanement la meme base.
        with db.engine.connect() as lock_conn:
            lock_conn.execute(
                text("SELECT pg_advisory_lock(hashtext(:key))"),
                {"key": LOCK_KEY},
            )
            try:
                inspector = inspect(db.engine)
                tables = set(inspector.get_table_names())

                # Une base avec alembic_version seule est un etat partiel,
                # jamais une base neuve.
                if not tables:
                    password = os.getenv("SUPERADMIN_PASSWORD", "").strip()
                    if not password:
                        fail(
                            "SUPERADMIN_PASSWORD est obligatoire pour initialiser "
                            "une base PostgreSQL vide."
                        )

                    from app.security.password_policy import validate_password_strength
                    password_error = validate_password_strength(password)
                    if password_error:
                        fail(
                            "SUPERADMIN_PASSWORD refuse par la politique : "
                            + password_error
                        )

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
                            "schema incomplet apres db.create_all(); tables "
                            "SQLAlchemy absentes: "
                            + ", ".join(sorted(missing_metadata))
                        )

                    print(f"Schema cree: {len(metadata_tables)} tables SQLAlchemy.")
                    print(f"Enregistrement du head Alembic V0: {expected_head}")
                    stamp(
                        directory=str(_BACKEND_ROOT / "migrations"),
                        revision=expected_head,
                    )

                    version_rows = [
                        row[0]
                        for row in db.session.execute(
                            text("SELECT version_num FROM alembic_version")
                        ).all()
                    ]
                    if version_rows != [expected_head]:
                        fail(
                            "verification Alembic echouee: version actuelle = "
                            + repr(version_rows)
                        )

                    print("Seed des roles et permissions...")
                    seed_roles(app)

                    print("Creation du Super Admin...")
                    user, created, changed = create_super_admin(
                        email=email,
                        username=username,
                        password=password,
                        force=False,
                    )
                    if user is None:
                        fail("Le Super Admin n'a pas pu etre cree.")

                    final_tables = set(inspect(db.engine).get_table_names())
                    missing_final = REQUIRED_TABLES - final_tables
                    if missing_final:
                        fail(
                            "verification finale echouee; tables absentes: "
                            + ", ".join(sorted(missing_final))
                        )

                    print("BOOTSTRAP PRODUCTION OK")
                    print(f"  Alembic head: {expected_head}")
                    print(f"  Super Admin: {email}")
                    print(f"  Compte cree: {created}")
                    print(
                        "  Changements: "
                        + (", ".join(changed) if changed else "aucun")
                    )
                    return

                # Toute base non vide doit etre coherente. Aucun auto-repair
                # silencieux n'est autorise au demarrage.
                if "alembic_version" not in tables:
                    fail(
                        "base PostgreSQL non vide sans alembic_version; "
                        "etat partiel/inconnu. Aucune modification effectuee."
                    )

                missing = REQUIRED_TABLES - tables
                if missing:
                    fail(
                        "base PostgreSQL partiellement initialisee; tables "
                        "obligatoires absentes: "
                        + ", ".join(sorted(missing))
                        + ". Aucune modification effectuee."
                    )

                version_rows = [
                    row[0]
                    for row in db.session.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).all()
                ]

                if version_rows != [expected_head]:
                    fail(
                        "revision Alembic inattendue; "
                        f"attendu={expected_head}, actuel={version_rows}. "
                        "Aucune modification effectuee."
                    )

                print(
                    "OK: base deja initialisee et coherente; "
                    "aucune creation ni reinitialisation effectuee."
                )
            finally:
                lock_conn.execute(
                    text("SELECT pg_advisory_unlock(hashtext(:key))"),
                    {"key": LOCK_KEY},
                )


if __name__ == "__main__":
    main()
