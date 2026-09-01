#!/usr/bin/env python
"""
Crée les tables de synchronisation desktop/web (favoris, colonnes, filtres, events).
En dev (SQLite) ou pour un bootstrap rapide, exécuter :
    python scripts/create_desk_tables.py
En prod, préférer : flask db migrate + flask db upgrade (Alembic).
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.desk_state import (
    DeskFavorite, DeskFilterPreset, DeskColumnConfig, SyncEvent
)

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        print("Création des tables de synchronisation (desk)...")
        db.create_all()
        print("Tables créées :", [
            DeskFavorite.__tablename__,
            DeskFilterPreset.__tablename__,
            DeskColumnConfig.__tablename__,
            SyncEvent.__tablename__,
        ])
