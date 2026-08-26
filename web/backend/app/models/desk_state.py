# web/backend/app/models/desk_state.py
# Modèles de préférences synchronisées (favoris, colonnes, filtres, events).
# Héritent de BaseModel : tenant_id, created_at, updated_at, is_active,
# created_by, updated_by. Scopés par user_id pour la cohérence web/desktop.

from app import db
from app.models.base import BaseModel
from datetime import datetime


class DeskFavorite(BaseModel):
    __tablename__ = 'desk_favorites'

    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False, index=True)
    path = db.Column(db.String(255), nullable=False)
    label = db.Column(db.String(255), nullable=True)
    data = db.Column(db.JSON, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'user_id', 'path', name='uq_desk_fav_tenant_user_path'),
    )

    def to_public(self):
        d = self.to_dict(exclude=['tenant_id', 'created_by', 'updated_by', 'is_active'])
        d['updatedAt'] = d.pop('updated_at')
        return d


class DeskFilterPreset(BaseModel):
    __tablename__ = 'desk_filter_presets'

    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False, index=True)
    module = db.Column(db.String(64), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    filters = db.Column(db.JSON, nullable=True)
    is_default = db.Column(db.Boolean, default=False)

    def to_public(self):
        d = self.to_dict(exclude=['tenant_id', 'created_by', 'updated_by', 'is_active'])
        d['updatedAt'] = d.pop('updated_at')
        d['createdAt'] = d.pop('created_at')
        return d


class DeskColumnConfig(BaseModel):
    __tablename__ = 'desk_column_configs'

    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False, index=True)
    module = db.Column(db.String(64), nullable=False, index=True)
    widths = db.Column(db.JSON, nullable=True)
    hidden = db.Column(db.JSON, nullable=True)
    sort = db.Column(db.JSON, nullable=True)
    version = db.Column(db.Integer, default=1)

    def to_public(self):
        d = self.to_dict(exclude=['tenant_id', 'created_by', 'updated_by', 'is_active'])
        d['updatedAt'] = d.pop('updated_at')
        return {
            'module': d['module'],
            'config': {
                'widths': d.get('widths') or {},
                'hidden': d.get('hidden') or [],
                'sort': d.get('sort') or [],
                'version': d.get('version', 1),
            },
        }


class SyncEvent(BaseModel):
    """Journal incrémental des mutations pour le temps-réel / pull polling."""
    __tablename__ = 'desk_sync_events'

    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False, index=True)
    entity = db.Column(db.String(32), nullable=False)  # favorite | column | filter | notification
    module = db.Column(db.String(64), nullable=True)
    payload = db.Column(db.JSON, nullable=True)
    revision = db.Column(db.BigInteger, nullable=False, index=True)

    def to_public(self):
        return {
            'id': self.id,
            'revision': self.revision,
            'entity': self.entity,
            'module': self.module,
            'payload': self.payload,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
