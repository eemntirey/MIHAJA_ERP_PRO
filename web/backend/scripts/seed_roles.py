#!/usr/bin/env python
"""
Script d'initialisation des roles et permissions par defaut
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.role_permission import RoleModel, Permission
from app.models.utilisateur import Role

def seed_roles(app=None):
    from app import db
    from app.security.permission_matrix import ROLE_PERMISSIONS, PERMISSION_DEFINITIONS

    DEFAULT_ROLES = [
        {'name': 'super_admin', 'display_name': 'Super Admin', 'description': 'Acces complet a toutes les fonctionnalites', 'is_default': True, 'is_system': True},
        {'name': 'admin', 'display_name': 'Admin', 'description': 'Acces administratif a toutes les ressources', 'is_default': True, 'is_system': True},
        {'name': 'manager', 'display_name': 'Manager', 'description': 'Gestion des produits, stock, ventes, utilisateurs et rapports', 'is_default': True, 'is_system': True},
        {'name': 'sales', 'display_name': 'Commercial', 'description': 'Gestion des ventes, clients et devis', 'is_default': True, 'is_system': True},
        {'name': 'stock', 'display_name': 'Stock', 'description': 'Gestion des stocks, produits et fournisseurs', 'is_default': True, 'is_system': True},
        {'name': 'accountant', 'display_name': 'Comptable', 'description': 'Gestion comptable, factures et paiements', 'is_default': True, 'is_system': True},
        {'name': 'rh', 'display_name': 'RH', 'description': 'Gestion des ressources humaines', 'is_default': True, 'is_system': True},
        {'name': 'user', 'display_name': 'Utilisateur', 'description': 'Utilisateur standard avec acces limite', 'is_default': True, 'is_system': True},
        {'name': 'support', 'display_name': 'Support', 'description': 'Assistance et support aux utilisateurs et clients', 'is_default': False, 'is_system': True},
        {'name': 'livreur', 'display_name': 'Livreur', 'description': 'Acces aux livraisons propres', 'is_default': False, 'is_system': True},
    ]

    for role_data in DEFAULT_ROLES:
        existing = RoleModel.query.filter_by(name=role_data['name']).first()
        if existing:
            existing.display_name = role_data['display_name']
            existing.description = role_data['description']
            existing.is_default = role_data['is_default']
            existing.is_system = role_data['is_system']
            existing.permissions = []
        else:
            existing = RoleModel(
                name=role_data['name'],
                display_name=role_data['display_name'],
                description=role_data['description'],
                is_default=role_data['is_default'],
                is_system=role_data['is_system'],
            )
            db.session.add(existing)
            db.session.flush()

        for perm_code in ROLE_PERMISSIONS.get(role_data['name'], []):
            if perm_code == '*':
                continue
            perm = Permission.query.filter_by(code=perm_code).first()
            if not perm:
                definition = PERMISSION_DEFINITIONS.get(perm_code, {})
                perm = Permission(
                    code=perm_code,
                    module=definition.get('module', perm_code.split('.')[0] if '.' in perm_code else 'general'),
                    action=definition.get('action', perm_code.split('.')[1] if '.' in perm_code else 'access'),
                    description=definition.get('description', perm_code),
                )
                db.session.add(perm)
                db.session.flush()
            if perm not in existing.permissions:
                existing.permissions.append(perm)

    db.session.commit()

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        seed_roles()
        print("Roles et permissions initialises avec succes!")
