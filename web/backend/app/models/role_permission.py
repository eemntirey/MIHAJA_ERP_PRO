from app.models.base import BaseModel
from app import db
from sqlalchemy import Table, Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime


role_permissions = Table(
    'role_permissions',
    db.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', db.DateTime, default=datetime.utcnow, nullable=False),
)


class Permission(BaseModel):
    __tablename__ = 'permissions'

    code = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))
    module = db.Column(db.String(100), index=True)
    action = db.Column(db.String(50))

    roles = relationship(
        'RoleModel',
        secondary=role_permissions,
        back_populates='permissions',
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<Permission {self.code}>'


class RoleModel(BaseModel):
    __tablename__ = 'roles'

    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100))
    description = db.Column(db.String(255))
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    is_system = db.Column(db.Boolean, default=False, nullable=False)

    permissions = relationship(
        'Permission',
        secondary=role_permissions,
        back_populates='roles',
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['permissions'] = [p.to_dict() for p in self.permissions] if self.permissions else []
        return data

    def __repr__(self):
        return f'<RoleModel {self.name}>'
