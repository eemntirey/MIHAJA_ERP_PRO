from app.models.utilisateur import Utilisateur
from app.security.auth import hash_password


def create_admin(username, email, password):
    hashed = hash_password(password)
    admin = Utilisateur(username=username, email=email, password_hash=hashed)
    return admin


if __name__ == '__main__':
    admin = create_admin('admin', 'admin@example.com', 'Admin123!')
    print('Admin user created: %s' % admin.username)
