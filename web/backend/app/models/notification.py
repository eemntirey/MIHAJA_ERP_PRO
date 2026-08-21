from app import db
from app.models.base import BaseModel
from datetime import datetime


class Notification(BaseModel):
    __tablename__ = 'notifications'

    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), nullable=False, default='info')
    read = db.Column(db.Boolean, nullable=False, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True)
    link = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        data = super().to_dict()
        data['title'] = self.title
        data['message'] = self.message
        data['type'] = self.type
        data['read'] = self.read
        data['read_at'] = self.read_at.isoformat() if self.read_at else None
        data['user_id'] = self.user_id
        data['link'] = self.link
        return data
