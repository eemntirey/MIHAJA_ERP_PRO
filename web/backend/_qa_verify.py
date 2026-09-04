"""Sonde QA temporaire : verifie le comportement live du serveur (a supprimer)."""
import sqlite3
import json
import urllib.request
import urllib.error

DB = r'C:\Users\eemntirey\Desktop\ERP_MM\MIHAJA_ERP_PRO\web\backend\erp.db'
BASE = 'http://localhost:5000/api/v1'


def req(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header('Content-Type', 'application/json')
    if token:
        r.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or '{}')
        except Exception:
            return e.code, {}


conn = sqlite3.connect(DB)
row = conn.execute(
    "SELECT id, nom FROM tenants WHERE nom LIKE 'QA-PROBE-%' ORDER BY id DESC LIMIT 1"
).fetchone()
print('QA TENANT:', row)
admin = conn.execute(
    "SELECT email FROM utilisateurs WHERE tenant_id=? AND role='admin'", (row[0],)
).fetchone()
print('QA ADMIN:', admin)
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('TABLES:', tables)
conn.close()

email = admin[0]
s, b = req('POST', '/auth/login', {'username': email, 'password': 'Companie123', 'device_id': 'qa-probe-device'})
print('LOGIN ->', s)
tok = b.get('access_token')

s, b = req('GET', '/users', token=tok)
print('GET /users (limite atteinte) ->', s, 'users=', len(b.get('users', [])))

s, b = req('POST', '/users', {'username': 'qa_overflow', 'email': 'qa_overflow@probe.mg',
                              'password': 'Employe123', 'nom': 'OVF', 'role': 'user'}, token=tok)
print('POST /users (depassement) ->', s, b.get('message', ''))

s, b = req('GET', '/dashboard/', token=tok)
print('GET /dashboard ->', s)
