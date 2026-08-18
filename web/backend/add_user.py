from app import create_app, db
from app.models.utilisateur import Utilisateur
from app.security.auth import hash_password

app = create_app()

with app.app_context():
    # Vérifier s'il existe déjà
    existing = Utilisateur.query.filter_by(email='testuser@example.com').first()
    if existing:
        print('Utilisateur test déjà existant:', existing.username)
    else:
        u = Utilisateur(
            username='testuser',
            email='testuser@example.com',
            password_hash=hash_password('Test1234'),
            nom='Test',
            prenom='User',
            role='USER',
            tenant_id=1,
        )
        db.session.add(u)
        db.session.commit()
        print('Utilisateur créé:', u.username)
