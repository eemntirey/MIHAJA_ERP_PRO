from app.models.base import BaseModel
from app import db
from sqlalchemy import Enum
import enum
from datetime import datetime

class Role(enum.Enum):
    SUPER_ADMIN = 'super_admin'
    ADMIN = 'admin'
    MANAGER = 'manager'
    SALES = 'sales'
    STOCK = 'stock'
    ACCOUNTANT = 'accountant'
    USER = 'user'
    
    def __str__(self):
        return self.value

class StatutUtilisateur(enum.Enum):
    ACTIF = 'actif'
    INACTIF = 'inactif'
    BLOQUE = 'bloque'
    EN_ATTENTE = 'en_attente'

class Utilisateur(BaseModel):
    __tablename__ = 'utilisateurs'
    
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    mobile = db.Column(db.String(20))
    
    role = db.Column(Enum(Role), default=Role.USER, nullable=False)
    custom_role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), index=True)
    statut = db.Column(Enum(StatutUtilisateur), default=StatutUtilisateur.ACTIF)
    
    custom_role = db.relationship('RoleModel', backref='users', foreign_keys='Utilisateur.custom_role_id')
    
    last_login = db.Column(db.DateTime)
    last_ip = db.Column(db.String(45))
    
    tenant = db.relationship('Tenant', back_populates='utilisateurs', foreign_keys='Utilisateur.tenant_id')
    clients = db.relationship('Client', back_populates='commercial', foreign_keys='Client.commercial_id', lazy='dynamic')
    ventes = db.relationship('Vente', back_populates='commercial', foreign_keys='Vente.commercial_id', lazy='dynamic')
    created_products = db.relationship('Produit', foreign_keys='Produit.created_by', lazy='dynamic')
    updated_products = db.relationship('Produit', foreign_keys='Produit.updated_by', lazy='dynamic')
    
    @property
    def full_name(self):
        if self.prenom and self.nom:
            return f"{self.prenom} {self.nom}"
        return self.username
    
    @property
    def is_admin(self):
        from app.security.roles import is_admin as _is_admin
        if self.custom_role_id:
            return any(p.code == 'admin.access' for p in (self.custom_role.permissions or []))
        return _is_admin(self.role)
    
    @property
    def is_super_admin(self):
        from app.security.roles import is_super_admin as _is_super_admin
        if self.custom_role_id:
            return any(p.code == 'super_admin.access' for p in (self.custom_role.permissions or []))
        return _is_super_admin(self.role)
    
    @property
    def is_manager(self):
        from app.security.roles import is_manager as _is_manager
        if self.custom_role_id:
            return any(p.code in ['manager.access', 'admin.access', 'super_admin.access'] for p in (self.custom_role.permissions or []))
        return _is_manager(self.role)
    
    def get_permissions(self):
        if self.custom_role_id and self.custom_role and self.custom_role.permissions:
            return [p.code for p in self.custom_role.permissions]
        from app.security.roles import PERMISSIONS
        role_name = self.role.value if hasattr(self.role, 'value') else self.role
        return PERMISSIONS.get(role_name, [])
    
    def has_permission(self, permission):
        from app.security.roles import has_permission
        return has_permission(self.id, permission)
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if 'password_hash' in data:
            del data['password_hash']
        if 'role' in data:
            data['role'] = str(self.role)
        if 'statut' in data:
            data['statut'] = str(self.statut)
        if 'custom_role_id' in data:
            if self.custom_role:
                data['custom_role'] = self.custom_role.to_dict()
            else:
                data['custom_role'] = None
        return data
    
    def __repr__(self):
        return f'<Utilisateur {self.username}>'
