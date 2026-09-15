import sys, os
sys.path.insert(0, 'C:/Users/eemntirey/Desktop/ERP_MM/MIHAJA_ERP_PRO/web/backend')
os.environ['FLASK_APP'] = 'app'
import dotenv
dotenv.load_dotenv('C:/Users/eemntirey/Desktop/ERP_MM/MIHAJA_ERP_PRO/web/backend/.env')
from app import create_app
app = create_app()
with app.app_context():
    from app.services.abonnement_service import AbonnementService
    from app import db
    # Utiliser le tenant 1 existant
    abn_gratuit, audit = AbonnementService.downgrade_to_free_plan(1, trigger='automatique', user_id=None)
    print('DOWNGRADE SUCCES:', abn_gratuit.id, audit.id, audit.nouveau_plan, audit.declencheur)
    # Nettoyer pour le test suivant
    db.session.delete(abn_gratuit)
    db.session.delete(audit)
    db.session.commit()
    # Test upgrade
    abn_pro, audit2 = AbonnementService.upgrade_to_pro(1, trigger='manuel', user_id=1)
    print('UPGRADE SUCCES:', abn_pro.id, audit2.id, audit2.nouveau_plan, audit2.declencheur)
    db.session.delete(abn_pro)
    db.session.delete(audit2)
    db.session.commit()
    print('Nettoyé upgrade - CONFIRMÉ')
