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
    RH = 'rh'
    LIVREUR = 'livreur'
    
    def __str__(self):
        return self.value

class StatutUtilisateur(enum.Enum):
    ACTIF = 'actif'
    INACTIF = 'inactif'
    BLOQUE = 'bloque'
    EN_ATTENTE = 'en_attente'

    def __str__(self):
        return self.value


class StatutAdmin(enum.Enum):
    ACTIVE = 'active'
    SUSPENDED = 'suspended'
    REVOKED = 'revoked'

    def __str__(self):
        return self.value

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
    admin_statut = db.Column(Enum(StatutAdmin), default=StatutAdmin.ACTIVE)
    device_id = db.Column(db.String(255), nullable=True, index=True)
    is_principal_admin = db.Column(db.Boolean, default=False, nullable=False)
    
    employee_key_hash = db.Column(db.String(255), nullable=True)
    employee_key_status = db.Column(db.String(20), nullable=True, default='active')
    
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
        if self.custom_role_id and self.custom_role is not None:
            return any(p.code == 'admin.access' for p in (self.custom_role.permissions or []))
        return _is_admin(self.role)

    @property
    def is_super_admin(self):
        from app.security.roles import is_super_admin as _is_super_admin
        if self.custom_role_id and self.custom_role is not None:
            return any(p.code == 'super_admin.access' for p in (self.custom_role.permissions or []))
        return _is_super_admin(self.role)

    @property
    def is_manager(self):
        from app.security.roles import is_manager as _is_manager
        if self.custom_role_id and self.custom_role is not None:
            return any(p.code in ['manager.access', 'admin.access', 'super_admin.access'] for p in (self.custom_role.permissions or []))
        return _is_manager(self.role)
    
    def get_permissions(self):
        if self.custom_role_id and self.custom_role and self.custom_role.permissions:
            return [p.code for p in self.custom_role.permissions]
        from app.security.permission_matrix import PERMISSIONS
        role_name = self.role.value if hasattr(self.role, 'value') else self.role
        return PERMISSIONS.get(role_name, [])
    
    def has_permission(self, permission):
        from app.security.roles import has_permission
        return has_permission(self.id, permission)
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if 'password_hash' in data:
            del data['password_hash']
        if 'employee_key_hash' in data:
            del data['employee_key_hash']
        if 'employee_key_status' in data:
            del data['employee_key_status']
        if 'role' in data:
            data['role'] = str(self.role)
        if 'statut' in data:
            data['statut'] = str(self.statut)
        if 'admin_statut' in data:
            data['admin_statut'] = (
                self.admin_statut.value
                if hasattr(self.admin_statut, 'value')
                else self.admin_statut
            )
        if 'custom_role_id' in data:
            if self.custom_role:
                data['custom_role'] = self.custom_role.to_dict()
            else:
                data['custom_role'] = None
        data['permissions'] = self.get_permissions()
        return data
    
    def mark_deleted(self):
        self.is_active = False
        self.email = f"deleted.{self.id}@{self.email.split('@')[-1]}" if '@' in (self.email or '') else f"deleted.{self.id}.{self.email}"
        self.username = f"deleted.{self.id}.{self.username}"
        db.session.add(self)

    def set_employee_key(self, key):
        import bcrypt
        salt = bcrypt.gensalt()
        self.employee_key_hash = bcrypt.hashpw(key.encode('utf-8'), salt).decode('utf-8')
        self.employee_key_status = 'active'
        return self.employee_key_hash

    def verify_employee_key(self, key):
        import bcrypt
        if not self.employee_key_hash:
            return False
        return bcrypt.checkpw(key.encode('utf-8'), self.employee_key_hash.encode('utf-8'))

    @staticmethod
    def generate_employee_key():
        import secrets
        return secrets.token_urlsafe(32)

    def __repr__(self):
        return f'<Utilisateur {self.username}>'

    @classmethod
    def free_inactive_credentials(cls, email=None, username=None):
        """Libère email/username d'un compte désactivé pour permettre une réinscription.

        Quand un compte a été supprimé (soft-delete), son email/username peut
        encore occuper la contrainte d'unicité (comptes supprimés avant la
        réécriture `deleted.<id>@...`). Cette méthode réécrit ces identifiants
        selon la même convention afin qu'une nouvelle inscription puisse
        réutiliser l'email/username. Les données du compte inactif restent
        conservées (is_active=False).
        """
        from sqlalchemy import or_

        conditions = []
        if email:
            conditions.append(cls.email == email)
        if username:
            conditions.append(cls.username == username)
        if not conditions:
            return

        candidates = cls.query.filter(
            cls.is_active == False,
            or_(*conditions),
        ).all()

        def _unique_email(user, base, domain):
            candidate = base
            n = 0
            while Utilisateur.query.filter(
                Utilisateur.email == candidate,
                Utilisateur.id != user.id,
            ).first() is not None:
                n += 1
                candidate = (
                    f"deleted.{user.id}-{n}@{domain}"
                    if domain
                    else f"deleted.{user.id}-{n}.{email}"
                )
            return candidate

        def _unique_username(user, base):
            candidate = base
            n = 0
            while Utilisateur.query.filter(
                Utilisateur.username == candidate,
                Utilisateur.id != user.id,
            ).first() is not None:
                n += 1
                candidate = f"{base}-{n}"
            return candidate

        changed = False
        for u in candidates:
            if email and u.email == email:
                domain = email.split('@')[-1] if '@' in (email or '') else None
                new_email = _unique_email(u, f"deleted.{u.id}@{domain}" if domain else f"deleted.{u.id}.{email}", domain)
                u.email = new_email
                changed = True
            if username and u.username == username:
                u.username = _unique_username(u, f"deleted.{u.id}.{u.username}")
                changed = True
            if changed:
                db.session.add(u)

        if changed:
            db.session.flush()
