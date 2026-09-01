import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.security.auth import hash_password

app = create_app()

with app.app_context():
    email = 'superadmin@mihaja.mg'
    username = 'superadmin'
    password = 'SuperAdmin123!'

    existing = Utilisateur.query.filter(
        Utilisateur.is_active == True,
        (Utilisateur.email == email) | (Utilisateur.username == username)
    ).first()

    if existing:
        print(f"Utilisateur existant: {existing.username} ({existing.email})")
        if existing.role != Role.SUPER_ADMIN:
            existing.role = Role.SUPER_ADMIN
            existing.statut = StatutUtilisateur.ACTIF
            existing.password_hash = hash_password(password)
            db.session.add(existing)
            db.session.commit()
            print("Role et mot de passe mis a jour en SUPER_ADMIN.")
        else:
            print("Le compte SUPER_ADMIN existe deja.")
    else:
        user = Utilisateur(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(user)
        db.session.commit()
        print(f"Super admin cree: {user.username} ({user.email})")
