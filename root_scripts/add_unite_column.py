import sys
sys.path.insert(0, 'web/backend')
from app import create_app, db

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        conn.execute(db.text('ALTER TABLE produits ADD COLUMN unite VARCHAR(50) DEFAULT "piece"'))
        conn.commit()
    insp = db.inspect(db.engine)
    columns = [col['name'] for col in insp.get_columns('produits')]
    print('Produits columns after ALTER:', columns)
    if 'unite' in columns:
        print('SUCCESS: unite column added')
    else:
        print('FAILED: unite column still missing')