import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.security.auth import hash_password, verify_password

app = create_app()
with app.app_context():
    sa = Utilisateur.query.filter_by(role=Role.SUPER_ADMIN).first()
    if sa:
        print('Username:', sa.username)
        print('Email:', sa.email)
        print('Password hash:', sa.password_hash)
        print('Verify Super123!:', verify_password('Super123!', sa.password_hash))
        print('Verify admin123:', verify_password('admin123', sa.password_hash))
    else:
        print('No super admin found')
