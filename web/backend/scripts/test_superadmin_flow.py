import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()
app.config['TESTING'] = True

with app.app_context():
    client = app.test_client()
    
    # First login
    login_payload = {
        'username': 'superadmin@mihaja.mg',
        'password': 'SuperAdmin123!'
    }
    
    login_response = client.post('/api/v1/auth/login', json=login_payload)
    print(f"Login status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.get_json()}")
        sys.exit(1)
    
    login_data = login_response.get_json()
    token = login_data.get('access_token')
    print(f"Token obtained: {bool(token)}")
    
    # Test super-admin endpoints
    headers = {'Authorization': f'Bearer {token}'}
    
    endpoints = [
        '/api/v1/super-admin/dashboard',
        '/api/v1/super-admin/tenants',
        '/api/v1/super-admin/subscriptions',
        '/api/v1/tenants/',
        '/api/v1/auth/super-admin/me',
    ]
    
    for endpoint in endpoints:
        resp = client.get(endpoint, headers=headers)
        print(f"\n{endpoint}: {resp.status_code}")
        body = resp.get_json()
        if isinstance(body, dict):
            msg = body.get('message', '')
            if msg:
                print(f"  Message: {msg}")
            else:
                keys = list(body.keys())[:3]
                print(f"  Keys: {keys}...")
        else:
            print(f"  Data type: {type(body)}")
