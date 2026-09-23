# -*- coding: utf-8 -*-
"""Creation (ou reparation) du compte SUPER_ADMIN de la plateforme MIHAJA ERP.

Le SUPER_ADMIN est le seul compte a acceder a l'espace prive (`super-admin/`).
Il n'est rattache a AUCUN tenant : `tenant_id = NULL` et
`is_principal_admin = False`.

Usage, depuis `web/backend` :

    # Base SQLite locale (dev) :
    .\\.venv\\Scripts\\python.exe scripts\\create_superadmin.py --sqlite

    # Base de .env (DATABASE_URL PostgreSQL) :
    $env:DATABASE_URL = 'postgresql+psycopg://erp_user:erp_password@localhost:5432/erp_db'
    $env:SUPERADMIN_PASSWORD = 'MonMotDePasse123'
    .\\.venv\\Scripts\\python.exe scripts\\create_superadmin.py

    # Identifiants explicites / reinitialisation / diagnostic :
    .\\.venv\\Scripts\\python.exe scripts\\create_superadmin.py --sqlite `
        --email root@mihaja.mg --username root --password 'MonMotDePasse123'
    .\\.venv\\Scripts\\python.exe scripts\\create_superadmin.py --sqlite --force
    .\\.venv\\Scripts\\python.exe scripts\\create_superadmin.py --sqlite --list

Idempotent : un compte existant n'est jamais duplique, son role/statut sont
corriges si besoin. `--force` reinitialise le mot de passe et invalide les
sessions ouvertes (token_version). Equivalent CLI : `python manage.py
create-superadmin` (voir manage.py).
"""
import os
import sys
from datetime import datetime

import click

# Racine du backend (web/backend) : derivee de l'emplacement du script (scripts/)
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
os.chdir(_BACKEND_ROOT)

DEFAULT_EMAIL = 'superadmin@mihaja.mg'
DEFAULT_USERNAME = 'superadmin'
DEFAULT_SQLITE_URL = 'sqlite:///./erp.db'


def _load_environment(use_sqlite=False):
    """Charge .env sans ecraser l'environnement, puis valide DATABASE_URL.

    `override=False` : une variable deja exportee dans le shell gagne, ce qui
    permet de viser une autre base sans modifier le fichier .env.
    """
    from dotenv import load_dotenv

    load_dotenv(os.path.join(_BACKEND_ROOT, '.env'))
    if use_sqlite:
        os.environ['DATABASE_URL'] = DEFAULT_SQLITE_URL

    if not os.getenv('DATABASE_URL'):
        click.secho(
            "ERREUR : DATABASE_URL est absent.\n"
            "  - definir .env (voir .env.example),\n"
            "  - ou lancer avec --sqlite (base locale erp.db),\n"
            "  - ou exporter DATABASE_URL dans le shell.",
            fg='red',
        )
        raise SystemExit(1)


def _ensure_schema(create_tables=False):
    """Verifie que la table utilisateurs existe (message actionnable sinon)."""
    from sqlalchemy import inspect

    from app import db

    if create_tables:
        db.create_all()
        click.echo('db.create_all() execute.')
    if 'utilisateurs' not in inspect(db.engine).get_table_names():
        click.secho(
            "ERREUR : la table 'utilisateurs' n'existe pas dans cette base.\n"
            "  Lancez les migrations (flask db upgrade) ou relancez "
            "avec --create-tables.",
            fg='red',
        )
        raise SystemExit(1)


def _find_user(email, username):
    from sqlalchemy import or_

    from app.models.utilisateur import Utilisateur

    return Utilisateur.query.filter(
        or_(Utilisateur.email == email, Utilisateur.username == username)
    ).first()


def _resolve_password(cli_password, required):
    """Priorite : --password, puis SUPERADMIN_PASSWORD, puis saisie masquee."""
    password = cli_password or os.getenv('SUPERADMIN_PASSWORD')
    if password or not required:
        return password
    import getpass

    password = getpass.getpass('Mot de passe Super Admin: ')
    confirm = getpass.getpass('Confirmer le mot de passe: ')
    if password != confirm:
        click.secho('Les mots de passe ne correspondent pas.', fg='red')
        raise SystemExit(1)
    return password


def create_super_admin(email, username, password=None, force=False):
    """Cree ou repare le compte SUPER_ADMIN. Retourne (user, created, changed)."""
    from app import db
    from app.models.utilisateur import (
        Role, StatutAdmin, StatutUtilisateur, Utilisateur,
    )
    from app.security.auth import hash_password

    user = _find_user(email, username)

    if user is None:
        user = Utilisateur(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
            admin_statut=StatutAdmin.ACTIVE,
            is_active=True,
            must_change_password=False,
            is_principal_admin=False,
            tenant_id=None,
        )
        db.session.add(user)
        db.session.commit()
        return user, True, ['created']

    changed = []
    if user.role != Role.SUPER_ADMIN:
        user.role = Role.SUPER_ADMIN
        changed.append('role')
    if not user.is_active:
        user.is_active = True
        changed.append('is_active')
    if user.statut != StatutUtilisateur.ACTIF:
        user.statut = StatutUtilisateur.ACTIF
        changed.append('statut')
    if user.admin_statut != StatutAdmin.ACTIVE:
        user.admin_statut = StatutAdmin.ACTIVE
        changed.append('admin_statut')
    if user.must_change_password:
        user.must_change_password = False
        changed.append('must_change_password')
    # Le super admin plateforme n'appartient a aucun tenant.
    if user.tenant_id is not None:
        user.tenant_id = None
        changed.append('tenant_id')
    if user.is_principal_admin:
        user.is_principal_admin = False
        changed.append('is_principal_admin')

    if force:
        if not password:
            raise ValueError(
                '--force exige un mot de passe (--password ou SUPERADMIN_PASSWORD).'
            )
        user.password_hash = hash_password(password)
        user.password_changed_at = datetime.utcnow()
        user.token_version = (user.token_version or 0) + 1
        changed.append('password (sessions invalidees)')

    if changed:
        db.session.add(user)
        db.session.commit()
    return user, False, changed


def list_super_admins():
    from app.models.utilisateur import Role, Utilisateur

    return Utilisateur.query.filter_by(role=Role.SUPER_ADMIN).all()


def _execute(email, username, password, force, create_tables, list_only,
             no_check_login):
    """Corps de la commande, execute dans un contexte applicatif deja ouvert."""
    from flask import current_app

    from app.security.password_policy import validate_password_strength

    click.echo(
        f"Base de donnees : {current_app.config['SQLALCHEMY_DATABASE_URI']}"
    )

    _ensure_schema(create_tables=create_tables)

    if list_only:
        admins = list_super_admins()
        click.echo(f"Super-admins ({len(admins)}) :")
        for admin in admins:
            click.echo(
                f"  id={admin.id} username={admin.username} "
                f"email={admin.email} is_active={admin.is_active} "
                f"statut={admin.statut} admin_statut={admin.admin_statut} "
                f"tenant_id={admin.tenant_id}"
            )
        return

    existing = _find_user(email, username)
    password = _resolve_password(password, required=force or existing is None)
    if password:
        error = validate_password_strength(password)
        if error:
            click.secho(f"Mot de passe refuse par la politique : {error}", fg='red')
            raise SystemExit(1)

    user, created, changed = create_super_admin(
        email=email, username=username, password=password, force=force,
    )

    if created:
        click.secho(
            f"Super admin cree : id={user.id}, username={user.username}, "
            f"email={user.email}, role={user.role}",
            fg='green',
        )
    else:
        details = ', '.join(changed) if changed else 'aucun changement'
        click.secho(
            f"Super admin deja present : id={user.id}, "
            f"username={user.username}, email={user.email} ({details})",
            fg='yellow',
        )

    if password and not no_check_login and (created or force):
        from app.security.auth import authenticate_user

        result, auth_error = authenticate_user(user.email, password)
        if auth_error or not result:
            click.secho(
                f"Verification login : ECHEC ({auth_error or 'aucun jeton'})",
                fg='red',
            )
            raise SystemExit(1)
        click.secho(
            'Verification login : OK (jeton emis en memoire, '
            'aucune requete HTTP).',
            fg='green',
        )

    click.echo(
        "\nEspace prive : super-admin/ (acces reserve au role super_admin)"
        f"\n  {user.email}"
    )


def run_with_fresh_app(email, username, password=None, force=False,
                       create_tables=False, list_only=False,
                       no_check_login=False, use_sqlite=False):
    """Entree reutilisable (commande `python manage.py create-superadmin`).

    L'environnement est recharge PUIS l'application reconstruite : manage.py
    cree deja une application au moment de l'import, donc un `--sqlite` ou un
    `DATABASE_URL` positionne apres coup ne serait pas pris en compte.
    """
    _load_environment(use_sqlite=use_sqlite)
    from app import create_app

    app = create_app()
    with app.app_context():
        return _execute(email, username, password, force, create_tables,
                        list_only, no_check_login)


@click.command(help=__doc__)
@click.option('--email', default=DEFAULT_EMAIL, show_default=True,
              help='Email du compte Super Admin.')
@click.option('--username', default=DEFAULT_USERNAME, show_default=True,
              help="Nom d'utilisateur du compte Super Admin.")
@click.option('--password', default=None,
              help='Mot de passe (sinon SUPERADMIN_PASSWORD puis saisie masquee).')
@click.option('--force', is_flag=True,
              help='Reinitialise le mot de passe si le compte existe deja.')
@click.option('--sqlite', 'use_sqlite', is_flag=True,
              help='Force la base locale sqlite:///./erp.db (cf. .env_sqlite).')
@click.option('--create-tables', 'create_tables', is_flag=True,
              help='Cree les tables manquantes (db.create_all) avant insertion.')
@click.option('--list', 'list_only', is_flag=True,
              help='Affiche seulement les super-admins existants.')
@click.option('--no-check-login', 'no_check_login', is_flag=True,
              help="N'effectue pas la verification d'authentification en memoire.")
def main(email, username, password, force, use_sqlite, create_tables,
         list_only, no_check_login):
    """Point d'entree `python scripts/create_superadmin.py`."""
    run_with_fresh_app(
        email=email,
        username=username,
        password=password,
        force=force,
        create_tables=create_tables,
        list_only=list_only,
        no_check_login=no_check_login,
        use_sqlite=use_sqlite,
    )


if __name__ == '__main__':
    main()

