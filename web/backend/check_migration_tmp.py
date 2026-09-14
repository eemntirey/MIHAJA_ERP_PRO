"""Smoke test temporaire : create_app + routes entrepots/produits."""
from app import create_app

app = create_app()
rules = [
    str(rule) for rule in app.url_map.iter_rules()
    if 'entrepot' in str(rule) or 'qr' in str(rule)
]
print(f"entrepots/qr routes ({len(rules)}) :")
for r in sorted(rules):
    print(f"  {r}")
