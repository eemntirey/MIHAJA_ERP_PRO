import json
from urllib import request

BASE = 'http://127.0.0.1:5000/api/v1'

# 1) Login
login_payload = {'username':'testuser@example.com','password':'Test1234','tenant_slug':'erp-commercial'}
req = request.Request(f'{BASE}/auth/login', data=json.dumps(login_payload).encode('utf-8'), headers={'Content-Type':'application/json'}, method='POST')
with request.urlopen(req) as r:
    resp = json.loads(r.read().decode('utf-8'))
    access = resp.get('access_token')
    refresh = resp.get('refresh_token')
    print('Login OK, access len', len(access) if access else None)

# 2) Call protected resource with invalid access token
bad_req = request.Request(f'{BASE}/produits', headers={'Authorization':'Bearer invalidtoken'}, method='GET')
try:
    with request.urlopen(bad_req) as r:
        print('Unexpected success', r.status)
except Exception as e:
    print('Protected call with invalid token failed as expected:', e)

# 3) Call refresh with refresh token in Authorization header
refresh_req = request.Request(f'{BASE}/auth/refresh', data=None, headers={'Authorization': f'Bearer {refresh}'}, method='POST')
with request.urlopen(refresh_req) as r2:
    r2b = json.loads(r2.read().decode('utf-8'))
    new_access = r2b.get('access_token')
    print('Refresh returned new access len', len(new_access) if new_access else None)

# 4) Retry protected resource with new access
retry_req = request.Request(f'{BASE}/produits', headers={'Authorization': f'Bearer {new_access}'}, method='GET')
try:
    with request.urlopen(retry_req) as r3:
        print('Retry success, status', r3.status)
        print('Body sample:', r3.read(200).decode('utf-8'))
except Exception as e:
    print('Retry failed:', e)
