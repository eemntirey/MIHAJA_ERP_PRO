from .settings import Config
from ..models.base import db


def init_db(app):
    app.config.from_object(Config)
    db.init_app(app)
    return db
