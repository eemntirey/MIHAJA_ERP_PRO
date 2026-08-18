import json
from urllib import request

url = 'http://127.0.0.1:5000/api/v1/auth/login'
payload = {
    'username': 'testuser@example.com',
    'password': 'Test1234',
    'tenant_slug': 'erp-commercial'
}

data = json.dumps(payload).encode('utf-8')
req = request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')

try:
    with request.urlopen(req) as resp:
        body = resp.read().decode('utf-8')
        print(resp.status)
        print(resp.getheaders())
        print(body)
        # Si login OK, essayer le refresh
        import json as _json
        data = _json.loads(body)
        refresh = data.get('refresh_token')
        if refresh:
            print('\nAttempting refresh...')
            refresh_req = request.Request(
                'http://127.0.0.1:5000/api/v1/auth/refresh',
                data=None,
                headers={'Authorization': f'Bearer {refresh}'},
                method='POST'
            )
            try:
                with request.urlopen(refresh_req) as r2:
                    b2 = r2.read().decode('utf-8')
                    print(r2.status)
                    print(r2.getheaders())
                    print(b2)
            except Exception as e2:
                print('Refresh error:', e2)
                if hasattr(e2, 'read'):
                    print(e2.read().decode('utf-8'))
except Exception as e:
    print('Error:', e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
