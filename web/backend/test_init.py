import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

print("Step 1: Starting...")

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

print("Step 2: Imports done")

db = SQLAlchemy()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test'
app.config['JWT_SECRET_KEY'] = 'test'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///erp_new.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

print("Step 3: DB initialized")

with app.app_context():
    print("Step 4: In context")
    db.create_all()
    print("Step 5: Tables created")

print("Done!")
