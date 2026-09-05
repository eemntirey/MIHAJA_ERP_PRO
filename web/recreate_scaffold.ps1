# recreate_all_files.ps1
Write-Host "--- Recreation de tous les fichiers ---" -ForegroundColor Green

# Creer les dossiers necessaires
New-Item -ItemType Directory -Path "backend\app\api\v1" -Force | Out-Null
New-Item -ItemType Directory -Path "backend\app\models" -Force | Out-Null
New-Item -ItemType Directory -Path "backend\app\services" -Force | Out-Null

# 1. Creer test.py
"from flask_restx import Namespace, Resource

ns = Namespace('test', description='Test API')

@ns.route('/')
class TestResource(Resource):
    def get(self):
        return {'message': 'API fonctionne'}, 200" | Out-File -FilePath "backend\app\api\v1\test.py" -Encoding UTF8

# 2. Creer __init__.py dans v1
"from . import test" | Out-File -FilePath "backend\app\api\v1\__init__.py" -Encoding UTF8

# 3. Creer __init__.py dans api
"from .v1 import test" | Out-File -FilePath "backend\app\api\__init__.py" -Encoding UTF8

# 4. Creer app/__init__.py complet
"from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_restx import Api
from flask_jwt_extended import JWTManager
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql+psycopg://erp_user:erp_password@localhost:5432/erp_db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret')

    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    jwt.init_app(app)

    api = Api(app, title='ERP Commercial API', version='1.0', doc='/docs/')

    from app.api.v1.test import ns as test_ns
    api.add_namespace(test_ns, path='/api/v1/test')

    @app.route('/')
    def index():
        return {'message': 'ERP Commercial API', 'status': 'running'}, 200

    @app.route('/health')
    def health():
        return {'status': 'healthy', 'database': 'connected'}, 200

    return app" | Out-File -FilePath "backend\app\__init__.py" -Encoding UTF8

# 5. Creer run.py
"from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))

    print('=' * 50)
    print('ERP Commercial API')
    print('=' * 50)
    print(f'Serveur: http://localhost:{port}')
    print(f'Documentation: http://localhost:{port}/docs')
    print('=' * 50)
    print('')

    app.run(debug=debug, host=host, port=port)" | Out-File -FilePath "backend\run.py" -Encoding UTF8

# 6. Creer models/__init__.py
"from app.models.base import BaseModel

__all__ = ['BaseModel']" | Out-File -FilePath "backend\app\models\__init__.py" -Encoding UTF8

# 7. Creer base.py
"from app import db
from datetime import datetime

class BaseModel(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        self.is_active = False
        db.session.commit()

    def to_dict(self):
        data = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            data[column.name] = value
        return data" | Out-File -FilePath "backend\app\models\base.py" -Encoding UTF8

# 8. Creer services/__init__.py
"# Services" | Out-File -FilePath "backend\app\services\__init__.py" -Encoding UTF8

# 9. Creer .env
"FLASK_APP=run.py
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=
JWT_SECRET_KEY=
DATABASE_URL=postgresql+psycopg://erp_user:erp_password@localhost:5432/erp_db
ENCRYPTION_KEY=" | Out-File -FilePath "backend\.env" -Encoding UTF8

# Messages de fin
Write-Host ""
Write-Host "[OK] Tous les fichiers ont ete generes avec succes !" -ForegroundColor Green
Write-Host ""
Write-Host "[INFO] Pour lancer l'application :" -ForegroundColor Cyan
Write-Host "   cd backend" -ForegroundColor White
Write-Host "   python run.py" -ForegroundColor White
Write-Host ""
