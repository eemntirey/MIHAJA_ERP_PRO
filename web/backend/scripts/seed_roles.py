#!/usr/bin/env python
"""
Script d'initialisation des roles et permissions par defaut
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.role_permission import RoleModel, Permission
from app.models.utilisateur import Role

app = create_app()

DEFAULT_ROLES = [
    {
        'name': 'super_admin',
        'display_name': 'Super Administrateur',
        'description': 'Acces complet a toutes les fonctionnalites',
        'is_default': True,
        'is_system': True,
        'permissions': ['*']
    },
    {
        'name': 'admin',
        'display_name': 'Administrateur',
        'description': 'Acces administratif a toutes les ressources',
        'is_default': True,
        'is_system': True,
        'permissions': ['*']
    },
    {
        'name': 'manager',
        'display_name': 'Manager',
        'description': 'Gestion des produits, stock, ventes, utilisateurs et rapports',
        'is_default': True,
        'is_system': True,
        'permissions': [
            'product.create', 'product.update', 'product.delete', 'product.view',
            'stock.view', 'stock.update',
            'sale.view', 'sale.create', 'sale.update',
            'user.view', 'user.create', 'user.update',
            'report.view',
            'client.view', 'client.create', 'client.update',
            'invoice.view', 'invoice.create', 'invoice.update',
            'payment.view', 'payment.create',
        ]
    },
    {
        'name': 'sales',
        'display_name': 'Commercial',
        'description': 'Gestion des ventes, clients et devis',
        'is_default': True,
        'is_system': True,
        'permissions': [
            'product.view',
            'sale.view', 'sale.create',
            'client.view', 'client.create', 'client.update',
            'quote.view', 'quote.create',
            'invoice.view',
        ]
    },
    {
        'name': 'stock',
        'display_name': 'Gestionnaire de Stock',
        'description': 'Gestion des stocks, produits et fournisseurs',
        'is_default': True,
        'is_system': True,
        'permissions': [
            'product.view', 'product.create', 'product.update',
            'stock.view', 'stock.update',
            'supplier.view', 'supplier.create', 'supplier.update',
            'purchase_order.view', 'purchase_order.create',
            'sale.view',
        ]
    },
    {
        'name': 'accountant',
        'display_name': 'Comptable',
        'description': 'Gestion comptable, factures et paiements',
        'is_default': True,
        'is_system': True,
        'permissions': [
            'product.view',
            'invoice.view', 'invoice.create', 'invoice.update',
            'payment.view', 'payment.create',
            'report.view',
            'sale.view',
            'client.view',
            'compte.view', 'compte.create', 'compte.update', 'compte.delete',
            'ecriture.view', 'ecriture.create', 'ecriture.update', 'ecriture.delete',
            'tresorerie.view', 'tresorerie.create', 'tresorerie.update', 'tresorerie.delete',
        ]
    },
    {
        'name': 'user',
        'display_name': 'Utilisateur',
        'description': 'Utilisateur standard avec acces limite',
        'is_default': True,
        'is_system': True,
        'permissions': [
            'product.view',
            'profile.view', 'profile.update',
        ]
    },
]

def seed_roles():
    with app.app_context():
        print("Initialisation des roles et permissions...")
        
        for role_data in DEFAULT_ROLES:
            existing = RoleModel.query.filter_by(name=role_data['name']).first()
            if existing:
                print(f"  Role '{role_data['name']}' existe deja, mise a jour...")
                existing.display_name = role_data['display_name']
                existing.description = role_data['description']
                existing.is_default = role_data['is_default']
                existing.is_system = role_data['is_system']
                existing.permissions = []
            else:
                print(f"  Creation du role '{role_data['name']}'...")
                existing = RoleModel(
                    name=role_data['name'],
                    display_name=role_data['display_name'],
                    description=role_data['description'],
                    is_default=role_data['is_default'],
                    is_system=role_data['is_system'],
                )
                db.session.add(existing)
            
            for perm_code in role_data['permissions']:
                if perm_code == '*':
                    continue
                perm = Permission.query.filter_by(code=perm_code).first()
                if not perm:
                    parts = perm_code.split('.')
                    perm = Permission(
                        code=perm_code,
                        module=parts[0] if parts else 'general',
                        action=parts[1] if len(parts) > 1 else 'access',
                        description=perm_code,
                    )
                    db.session.add(perm)
                    db.session.flush()
                if perm not in existing.permissions:
                    existing.permissions.append(perm)
        
        db.session.commit()
        print("Roles et permissions initialises avec succes!")

if __name__ == '__main__':
    seed_roles()
