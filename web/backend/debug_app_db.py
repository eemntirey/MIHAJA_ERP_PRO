import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models.utilisateur import Utilisateur

app = create_app()
with app.app_context():
    print(f"Instance path: {app.instance_path}")
    db_path = os.path.join(app.instance_path, 'erp.db')
    print(f"DB path: {db_path}")
    print(f"DB exists: {os.path.exists(db_path)}")
    
    if os.path.exists(db_path):
        print(f"DB size: {os.path.getsize(db_path)}")
    
    # Check tables via SQLAlchemy
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Tables via inspector: {tables}")
    
    # Check if utilisateurs table exists
    print(f"utilisateurs in tables: {'utilisateurs' in tables}")
    
    # Try to query
    try:
        count = db.session.query(Utilisateur).count()
        print(f"Utilisateur count: {count}")
    except Exception as e:
        print(f"Query error: {e}")
