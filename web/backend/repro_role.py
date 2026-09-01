import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret'
os.environ['FLASK_ENV'] = 'testing'

print('1: starting')
import sys
sys.stdout.flush()

from app import create_app, db
print('2: imported create_app')
sys.stdout.flush()

from app.models.tenant import Tenant, StatutTenant
print('3: imported models')
sys.stdout.flush()

app = create_app()
print('4: created app')
sys.stdout.flush()

app.config['TESTING'] = True
print('5: set testing')
sys.stdout.flush()

with app.app_context():
    print('6: in app context')
    sys.stdout.flush()
    db.drop_all()
    print('7: dropped all')
    sys.stdout.flush()
    db.create_all()
    print('8: created all')
    sys.stdout.flush()
