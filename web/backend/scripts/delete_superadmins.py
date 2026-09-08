
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration de l'application Flask
from app import create_app, db
from app.models.utilisateur import Utilisateur, Role

# Créer l'application dans son contexte
app = create_app()
with app.app_context():
    try:
        # Compter les super-admins avant suppression
        super_admins_before = Utilisateur.query.filter_by(role=Role.SUPER_ADMIN).count()
        print(f'Nombre de super-admins avant suppression : {super_admins_before}')
        
        # Récupérer les super-admins pour les lister avant suppression (optionnel)
        if super_admins_before > 0:
            admins = Utilisateur.query.filter_by(role=Role.SUPER_ADMIN).all()
            print('Super-admins trouvés :')
            for admin in admins:
                print(f'  - ID: {admin.id}, Username: {admin.username}, Email: {admin.email}')
        
        # Supprimer tous les super-admins
        deleted = Utilisateur.query.filter_by(role=Role.SUPER_ADMIN).delete()
        db.session.commit()
        
        # Compter après suppression
        super_admins_after = Utilisateur.query.filter_by(role=Role.SUPER_ADMIN).count()
        print(f'Nombre de super-admins après suppression : {super_admins_after}')
        print(f'Nombre de comptes supprimés : {deleted}')
        
        if deleted > 0:
            print('✅ Suppression réussie')
        else:
            print('ℹ️ Aucun super-admin à supprimer')
            
    except Exception as e:
        print(f'❌ Erreur : {str(e)}')
        db.session.rollback()
        raise

