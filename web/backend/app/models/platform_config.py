# -*- coding: utf-8 -*-
"""Configuration globale plateforme (singleton).

Gère notamment le mode d'abonnement global :
- is_subscription_active == False : Mode Inactif (mode de lancement, plan Pro offert, quotas souples)
- is_subscription_active == True : Mode Actif (mode commercial classique avec cycle payant)
"""
from datetime import datetime
from app import db


class PlatformConfig(db.Model):
    __tablename__ = 'platform_configs'

    id = db.Column(db.Integer, primary_key=True)
    is_subscription_active = db.Column(db.Boolean, nullable=False, default=False)
    # Surcharges persistants pour les paramètres éditables des plans.
    # Format: {"gratuit": {"prix": 0, "duree_jours": 30}, ...}
    plans_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'is_subscription_active': bool(self.is_subscription_active),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
        }

    @classmethod
    def get_config(cls):
        """Récupère la configuration singleton (id=1) ou l'initialise si absente."""
        cfg = cls.query.filter_by(id=1).first()
        if not cfg:
            cfg = cls(id=1, is_subscription_active=False)
            db.session.add(cfg)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                cfg = cls.query.filter_by(id=1).first() or cfg
        return cfg
