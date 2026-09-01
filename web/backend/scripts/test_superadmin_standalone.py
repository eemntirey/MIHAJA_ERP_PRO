import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()
app.config['TESTING'] = True

with app.app_context():
    client = app.test_client()
    
    # Login like the super-admin app does
    login_payload = {
        'username': 'superadmin@mihaja.mg',
        'password': 'SuperAdmin123!'
    }
    
    response = client.post('/api/v1/auth/login', json=login_payload)
    print(f"Login status: {response.status_code}")
    data = response.get_json()
    
    if response.status_code == 200:
        access_token = data.get('access_token')
        refresh_token = data.get('refresh_token')
        user_data = data.get('user')
        
        print(f"Access token: {bool(access_token)}")
        print(f"Refresh token: {bool(refresh_token)}")
        print(f"User role: {user_data.get('role')}")
        print(f"User email: {user_data.get('email')}")
        
        # Test confirmSession like the super-admin app does
        headers = {'Authorization': f'Bearer {access_token}'}
        confirm_resp = client.post('/api/v1/super-admin/auth/login', headers=headers)
        print(f"\nConfirm session status: {confirm_resp.status_code}")
        confirm_data = confirm_resp.get_json()
        print(f"Confirm response: {confirm_data}")
    else:
        print(f"Error: {data}")
