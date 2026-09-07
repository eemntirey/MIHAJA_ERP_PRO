# -*- coding: utf-8 -*-
"""JWT Token Blocklist — révocation réelle des tokens.

Stocke les JTI (JWT ID) des tokens révoqués jusqu'à leur expiration naturelle.
Utilisé par flask-jwt-extended via @jwt.token_in_blocklist_loader.
"""
from datetime import datetime
from app import db


class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(16), nullable=False, default='access')  # access | refresh
    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True, index=True)
    revoked_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)

    def __repr__(self):
        return f'<TokenBlocklist jti={self.jti} type={self.token_type}>'

    @classmethod
    def is_revoked(cls, jti: str) -> bool:
        if not jti:
            return False
        return db.session.query(cls.id).filter_by(jti=jti).first() is not None

    @classmethod
    def revoke(cls, jti: str, expires_at, token_type: str = 'access', user_id=None):
        """Ajoute un token à la blocklist (idempotent)."""
        if not jti:
            return None
        existing = cls.query.filter_by(jti=jti).first()
        if existing:
            return existing
        entry = cls(
            jti=jti,
            token_type=token_type or 'access',
            user_id=user_id,
            expires_at=expires_at,
        )
        db.session.add(entry)
        return entry

    @classmethod
    def purge_expired(cls):
        """Supprime les entrées dont expires_at est passé (nettoyage)."""
        now = datetime.utcnow()
        deleted = cls.query.filter(cls.expires_at < now).delete()
        return deleted
