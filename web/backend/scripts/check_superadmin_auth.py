#!/usr/bin/env python
"""
Script pour créer un super admin si il n'existe pas et tester l'authentification.
Ce script suppose que le backend Flask est en cours d'exécution sur localhost:5000
"""
import sys
import os
import requests
import json

# Configuration depuis .env
# Racine du backend (web/backend) : derivee de l'emplacement du script (scripts/)
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND_ROOT)
os.chdir(_BACKEND_ROOT)

from app import create_app
from app.security.auth import hash_password
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur

# Configuration pour tester
backend_url = "http://127.0.0.1:5000"

print("=" * 60)
print("MIHAJA ERP - Test d'authentification Super Admin")
print("=" * 60)

# Configuration de l'application Flask (utilisée uniquement pour la création de données en base de données)
os.environ['DATABASE_URL'] = 'postgresql+psycopg://postgres:eemntirey@localhost:5432/erp'
os.environ['JWT_SECRET_KEY'] = 'test-secret'
os.environ['SECRET_KEY'] = 'test-secret'

app = create_app()

# Test 1: Se connecter avec les identifiants connus depuis les tests
def test_login(email, password, description):
    print(f"\n{'=' * 40}")
    print(f"Test: {description}")
    print(f"Email: {email}")
    print(f"{'=' * 40}")
    
    url = f"{backend_url}/api/v1/auth/login"
    data = {'username': email, 'password': password}
    
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            token = result.get('access_token')
            if token:
                print(f"✓ Login réussi ! Token reçu: {token[:30]}...")
                
                # Test /auth/me endpoint
                me_url = f"{backend_url}/api/v1/auth/me"
                headers = {'Authorization': f'Bearer {token}'}
                me_response = requests.get(me_url, headers=headers, timeout=10)
                print(f"Status /auth/me: {me_response.status_code}")
                print(f"Response /auth/me: {me_response.text}")
                
                # Test /super-admin/me endpoint
                sa_url = f"{backend_url}/api/v1/super-admin/me"
                sa_response = requests.get(sa_url, headers=headers, timeout=10)
                print(f"Status /super-admin/me: {sa_response.status_code}")
                print(f"Response /super-admin/me: {sa_response.text}")
                
                return True
            else:
                print("✗ Réponse de login invalide - pas de token")
        else:
            result = response.json() if response.text else {}
            print(f"✗ Échec du login: {result.get('message', 'Erreur inconnue')}")
    except Exception as e:
        print(f"✗ Erreur de connexion: {e}")
    
    return False

# Test 2: Créer un super admin si il n'existe pas
print("\n" + "=" * 60)
print("Test 2: Création d'un super admin")
print("=" * 60)

with app.app_context():
    # Vérifier si un super admin existe déjà
    existing = Utilisateur.query.filter_by(email='super@x.mg').first()
    if existing:
        print(f"✓ Super admin existe déjà: {existing.username} ({existing.email}), rôle: {existing.role}")
    else:
        print("✓ Création d'un nouveau super admin...")
        super_admin = Utilisateur(
            username='super',
            email='super@x.mg',
            password_hash=hash_password('Super123!'),
            role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
        )
        
        from app import db
        db.session.add(super_admin)
        db.session.commit()
        
        print(f"✓ Super admin créé: id={super_admin.id}, username={super_admin.username}, email={super_admin.email}")

print("\n" + "=" * 60)
print("Test 3: Authentification Super Admin")
print("=" * 60)

# Essayer de se connecter avec les identifiants connus
success = test_login('super@x.mg', 'Super123!', 'Super Admin connu depuis les tests')

if not success:
    print("\n" + "=" * 60)
    print("Test 4: Tentative de connexion avec l'admin principal de Mada Distribution")
    print("=" * 60)
    
    # Depuis les tests, il y a un tenant 'mada' avec admin 'mada'
    success2 = test_login('mada', 'Test1234!', 'Admin principal Mada Distribution')

print("\n" + "=" * 60)
print("Résumé")
print("=" * 60)
print(f"✓ Backend: {backend_url}")
print("✓ Identifiants connus depuis les tests:")
print("  - super@x.mg / Super123! (Super Admin)")
print("  - mada / Test1234! (Admin principal Mada Distribution)")
print("\n🔍 Si aucun des tests ci-dessus ne réussit:")
print("   1. Assurez-vous que le backend Flask est en cours d'exécution sur le port 5000")
print("   2. Vérifiez que la base de données PostgreSQL contient les tables nécessaires")
print("   3. Vérifiez que l'utilisateur 'postgres' a accès à la base de données 'erp'")
print("\nPour démarrer le backend:")
print("   cd web/backend")
print("   .venv\\Scripts\\python.exe run.py")