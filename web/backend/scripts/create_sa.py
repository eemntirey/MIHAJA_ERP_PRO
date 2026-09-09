import os
import sys

# Set environment variables before importing app
os.environ['DATABASE_URL'] = 'postgresql+psycopg://postgres:eemntirey@localhost:5432/erp'
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['JWT_SECRET_KEY'] = 'test-secret'

# Racine du backend (web/backend) : derivee de l'emplacement du script (scripts/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.security.auth import hash_password
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur

app = create_app()
with app.app_context():
    # Check existing users
    existing = Utilisateur.query.filter_by(email='super@x.mg').first()
    if existing:
        print(f"Super admin already exists: id={existing.id}, username={existing.username}, role={existing.role}")
    else:
        super_admin = Utilisateur(
            username='super',
            email='super@x.mg',
            password_hash=hash_password('Super123!'),
            role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(super_admin)
        db.session.commit()
        print(f"Super admin created successfully: id={super_admin.id}, username={super_admin.username}, email={super_admin.email}, role={super_admin.role}")

    # List all users
    users = [(u.id, u.username, u.email, str(u.role)) for u in Utilisateur.query.all()]
    print(f"Total users: {len(users)}")
    for u in users:
        print(f"  {u}")

print("Done")