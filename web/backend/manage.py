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

@app.cli.command("seed-data")
def seed_data():
    """Remplit la base de données avec des données de test"""
    # Note: Create a seeds.py module to implement this functionality
    click.echo(" seed_all() function not implemented. Please create app/seeds.py.")

if __name__ == '__main__':
    app.cli()