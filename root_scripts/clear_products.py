import sys
sys.path.insert(0, 'web/backend')
from app import create_app, db

app = create_app()
with app.app_context():
    from app.models.produit import Produit
    Produit.query.delete()
    db.session.commit()
    print('Products cleared')