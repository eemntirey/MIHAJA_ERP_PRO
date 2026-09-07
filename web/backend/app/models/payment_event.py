
import json

from app.models.base import BaseModel
from app import db
from datetime import datetime
from sqlalchemy.types import TypeDecorator, TEXT


class JSONEncodedDict(TypeDecorator):
    impl = TEXT
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)


class PaymentEvent(BaseModel):
    __tablename__ = 'payment_events'

    payment_id = db.Column(db.Integer, db.ForeignKey('paiements.id'), nullable=False, index=True)
    event_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False)
    payload = db.Column(JSONEncodedDict, nullable=False)
    signature = db.Column(db.String(255))
    processed = db.Column(db.Boolean, default=False, nullable=False)
    processed_at = db.Column(db.DateTime)

    payment = db.relationship('Paiement', backref='events')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<PaymentEvent {self.event_id} processed={self.processed}>'
