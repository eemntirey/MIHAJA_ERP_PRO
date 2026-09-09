import sys
import os
# Racine du backend (web/backend) : derivee de l'emplacement du script (scripts/)
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND_ROOT)
os.chdir(_BACKEND_ROOT)

# Configure database URL
os.environ['DATABASE_URL'] = 'postgresql+psycopg://postgres:eemntirey@localhost:5432/erp'

from app import create_app, db
from app.security.auth import hash_password
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur

app = create_app()
with app.app_context():
    # Check if super admin user already exists
    existing = Utilisateur.query.filter_by(email='super@x.mg').first()
    if existing:
        print(f"Super admin already exists: id={existing.id}, username={existing.username}, role={existing.role}")
    else:
        # Create super admin user
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

    # Now test authentication
    from app.security.auth import authenticate_user
    result, error = authenticate_user('super@x.mg', 'Super123!')
    if error:
        print(f"Auth error: {error}")
    elif result:
        print(f"Auth success! result: {result}")
        # Test the me endpoint
        import requests
        r = requests.post('http://127.0.0.1:5000/api/v1/auth/login', json={'username': 'super@x.mg', 'password': 'Super123!'})
        print(f"Login response: {r.status_code} - {r.text}")
        if r.status_code == 200:
            data = r.json()
            access_token = data.get('access_token')
            if access_token:
                r2 = requests.get('http://127.0.0.1:5000/api/v1/auth/me', headers={'Authorization': f'Bearer {access_token}'})
                print(f"Me endpoint: {r2.status_code} - {r2.text}")
    else:
        print("Auth failed with no result")