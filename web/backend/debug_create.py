import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models.utilisateur import Utilisateur

print(f"Current dir: {os.getcwd()}")
print(f"Utilisateur table: {Utilisateur.__tablename__}")

app = create_app()
with app.app_context():
    print(f"DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Engine: {db.engine}")
    print(f"Tables in metadata: {list(db.metadata.tables.keys())[:5]}...")
    db.create_all()
    print("create_all done")
    
    # Check if file was created/modified
    db_path = os.path.join(os.getcwd(), 'erp.db')
    if os.path.exists(db_path):
        print(f"DB file exists: {db_path}, size: {os.path.getsize(db_path)}")
    else:
        print(f"DB file NOT found at: {db_path}")
    
    conn = db.engine.connect()
    cursor = conn.connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    conn.close()
