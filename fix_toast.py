import os, re
files = [
    'desk/src/pages/Accounting.jsx', 'desk/src/pages/Delivery.jsx', 'desk/src/pages/Documents.jsx',
    'desk/src/pages/HR.jsx', 'desk/src/pages/Payments.jsx', 'desk/src/pages/Purchases.jsx', 'desk/src/pages/Sales.jsx',
    'web/frontend/src/pages/Accounting.jsx', 'web/frontend/src/pages/Delivery.jsx', 'web/frontend/src/pages/Documents.jsx',
    'web/frontend/src/pages/HR.jsx', 'web/frontend/src/pages/Payments.jsx', 'web/frontend/src/pages/Purchases.jsx',
    'web/frontend/src/pages/Sales.jsx'
]
for f in files:
    if not os.path.exists(f):
        continue
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    # Remove lines containing toast.warning(`Chargement partiel: ...`)
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'toast.warning(' in line and 'Chargement partiel' in line:
            continue
        new_lines.append(line)
    content = '\n'.join(new_lines)
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
    print('Fixed', f)
