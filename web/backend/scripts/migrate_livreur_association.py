#!/usr/bin/env python
"""
Migration : ajout de la colonne utilisateur_id sur la table livreurs.

Cette colonne permet d'associer une fiche Livreur à un compte Utilisateur.
Elle est nullable et unique : un utilisateur ne peut être associé qu'à un seul livreur,
et un livreur peut exister sans compte.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text


def migrate():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        engine = db.engine
        with engine.connect() as conn:
            try:
                conn.execute(text('ALTER TABLE livreurs ADD COLUMN utilisateur_id INTEGER REFERENCES utilisateurs(id)'))
                conn.commit()
                print('Colonne utilisateur_id ajoutee.')
            except Exception as e:
                if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
                    print('Colonne utilisateur_id existe deja, migration ignoree.')
                else:
                    print(f'Erreur lors de l\'ajout de la colonne: {e}')
                    raise

            try:
                conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS idx_livreur_utilisateur_id ON livreurs (utilisateur_id)'))
                conn.commit()
                print('Index unique sur utilisateur_id cree.')
            except Exception as e:
                if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                    print('Index unique existe deja, migration ignoree.')
                else:
                    print(f'Erreur lors de la creation de l\'index: {e}')
                    raise

        print('Migration terminee.')


if __name__ == '__main__':
    migrate()
