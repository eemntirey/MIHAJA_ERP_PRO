#!/usr/bin/env python
"""
Script de creation des tables de la base de donnees
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.utilisateur import Utilisateur
from app.models.role_permission import RoleModel, Permission
from app.models.tenant import Tenant

app = create_app()

def create_tables():
    with app.app_context():
        print("Creation des tables...")
        db.create_all()
        print("Tables creees avec succes!")

if __name__ == '__main__':
    create_tables()
