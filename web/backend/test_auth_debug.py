import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models.utilisateur import Utilisateur

app = create_app()
with app.app_context():
    try:
        user = Utilisateur.query.filter_by(email='superadmin@test.com').first()
        if user:
            print(f"Found user: {user.username} ({user.email})")
        else:
            print("User superadmin@test.com not found")
    except Exception as e:
        print(f"Error: {e}")
