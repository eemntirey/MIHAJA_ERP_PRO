from app.models.base import BaseModel
from app import db
from datetime import datetime, timedelta
import secrets
import hashlib


class PasswordResetToken(BaseModel):
    __tablename__ = 'password_reset_tokens'

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.id'),
        nullable=False,
        index=True
    )
    token = db.Column(db.String(255), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    ip_address = db.Column(db.String(45))

    user = db.relationship(
        'Utilisateur',
        foreign_keys=[user_id],
        backref=db.backref('password_reset_tokens', lazy='dynamic')
    )

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(raw_token):
        """Digest déterministe SHA-256 du token brut.

        Le token est généré via secrets.token_urlsafe(32) (256 bits aléatoires) :
        un digest déterministe est donc aussi sûr qu'un hash lent à forcer,
        tout en permettant une requête ciblée et indexée (colonne `token`,
        unique + indexée) sans aucun scan global de la table.
        """
        return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

    @staticmethod
    def verify_token(raw_token, stored_hash):
        return PasswordResetToken.hash_token(raw_token) == stored_hash

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self):
        return not self.used and not self.is_expired

    @classmethod
    def find_by_raw_token(cls, raw_token):
        """Recherche ciblée et indexée d'un token non utilisé et non expiré."""
        return cls.query.filter(
            cls.token == cls.hash_token(raw_token),
            cls.used == False,
            cls.expires_at > datetime.utcnow(),
        ).first()

    @classmethod
    def find_valid_token(cls, user_id, raw_token):
        candidates = cls.query.filter_by(
            user_id=user_id,
            used=False,
        ).all()
        for candidate in candidates:
            if candidate.verify_token(raw_token, candidate.token):
                return candidate
        return None
