import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.ai.training import train_models

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        print("🤖 Entraînement des modèles IA en cours...")
        result = train_models()
        print("✅ Entraînement terminé :")
        print(result)

