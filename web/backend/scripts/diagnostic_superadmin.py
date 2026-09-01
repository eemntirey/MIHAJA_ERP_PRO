import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.security.auth import verify_password

app = create_app()

with app.app_context():
    user = Utilisateur.query.filter(
        Utilisateur.is_active == True,
        (Utilisateur.email == 'superadmin@mihaja.mg') | (Utilisateur.username == 'superadmin')
    ).first()

    if not user:
        print("Utilisateur introuvable")
    else:
        print(f"ID: {user.id}")
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        print(f"Statut: {user.statut}")
        print(f"Tenant ID: {user.tenant_id}")
        print(f"Admin statut: {user.admin_statut}")
        print(f"Is active: {user.is_active}")
        print(f"Password hash present: {bool(user.password_hash)}")

        password = 'SuperAdmin123!'
        match = verify_password(password, user.password_hash)
        print(f"Password match for '{password}': {match}")
