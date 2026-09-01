import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()
app.config['TESTING'] = True

with app.app_context():
    client = app.test_client()
    
    payload = {
        'username': 'superadmin@mihaja.mg',
        'password': 'SuperAdmin123!'
    }
    
    response = client.post('/api/v1/auth/login', json=payload)
    print(f"Status: {response.status_code}")
    print(f"Body: {response.get_json()}")
