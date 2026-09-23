import click
from flask.cli import with_appcontext
from app import create_app, db
from app.models.utilisateur import Utilisateur, Role
from app.security.auth import hash_password
import getpass

app = create_app()

@app.cli.command("create-admin")
@click.argument('email')
@click.argument('username')
def create_admin(email, username):
    """Crée un administrateur"""
    password = getpass.getpass("Mot de passe: ")
    password2 = getpass.getpass("Confirmer le mot de passe: ")
    
    if password != password2:
        click.echo("Les mots de passe ne correspondent pas")
        return
    
    if Utilisateur.query.filter_by(email=email).first():
        click.echo("Cet email existe déjà")
        return
    
    if Utilisateur.query.filter_by(username=username).first():
        click.echo("Ce nom d'utilisateur existe déjà")
        return
    
    admin = Utilisateur(
        email=email,
        username=username,
        password_hash=hash_password(password),
        role=Role.ADMIN,
        is_active=True
    )
    db.session.add(admin)
    db.session.commit()
    click.echo(f"Admin {username} créé avec succès!")

@app.cli.command("create-superadmin")
@click.option('--email', default='superadmin@mihaja.mg', show_default=True,
              help='Email du compte Super Admin.')
@click.option('--username', default='superadmin', show_default=True,
              help="Nom d'utilisateur du compte Super Admin.")
@click.option('--password', default=None,
              help='Sinon SUPERADMIN_PASSWORD, puis saisie masquee.')
@click.option('--force', is_flag=True,
              help='Réinitialise le mot de passe du compte existant.')
@click.option('--sqlite', 'use_sqlite', is_flag=True,
              help='Force sqlite:///./erp.db (base locale de dev).')
@click.option('--create-tables', 'create_tables', is_flag=True,
              help='Crée les tables manquantes avant insertion.')
@click.option('--list', 'list_only', is_flag=True,
              help='Affiche les super-admins existants.')
def create_superadmin(email, username, password, force, use_sqlite,
                      create_tables, list_only):
    """Crée le compte SUPER_ADMIN de la plateforme (idempotent).

    Le compte n'est rattaché à aucun tenant (tenant_id = NULL) et seul le rôle
    super_admin peut accéder à l'espace privé super-admin/.
    """
    # Source unique de vérité : scripts/create_superadmin.py. On reconstruit une
    # application, car celle importée ci-dessus a été créée avant que --sqlite /
    # DATABASE_URL ne soit appliqué.
    from scripts.create_superadmin import run_with_fresh_app

    run_with_fresh_app(
        email=email,
        username=username,
        password=password,
        force=force,
        create_tables=create_tables,
        list_only=list_only,
        use_sqlite=use_sqlite,
    )


@app.cli.command("seed-data")
def seed_data():
    """Remplit la base de données avec des données de test"""
    # Note: Create a seeds.py module to implement this functionality
    click.echo(" seed_all() function not implemented. Please create app/seeds.py.")

if __name__ == '__main__':
    app.cli()