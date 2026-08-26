from decimal import Decimal
from datetime import datetime, date
from app import db

class BaseModel(db.Model):
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    
    def save(self):
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        self.is_active = False
        db.session.commit()
    
    def hard_delete(self):
        db.session.delete(self)
        db.session.commit()
    
    def to_dict(self, exclude=None):
        data = {}
        exclude = exclude or []
        for column in self.__table__.columns:
            if column.name in exclude:
                continue
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, date):
                value = value.isoformat()
            elif isinstance(value, Decimal):
                value = float(value)
            data[column.name] = value
        return data


class BaseTenantModel(BaseModel):
    __abstract__ = True
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
