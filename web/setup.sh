#!/bin/bash

echo "Installation de l'ERP Commercial..."

# Backend
echo "Installation du backend..."
cd backend
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd ..

# Frontend
echo "Installation du frontend..."
cd frontend
npm install
cd ..

# Docker (optionnel)
echo "Lancement des conteneurs Docker..."
docker-compose up -d

echo "Installation terminée!"
echo "Backend: http://localhost:5000"
echo "Documentation API: http://localhost:5000/docs"
echo "Frontend: http://localhost:3000"
echo "PhpMyAdmin: http://localhost:8080 (user: root, password: rootpassword)"