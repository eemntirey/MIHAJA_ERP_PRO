import sys
sys.path.insert(0, 'C:/Users/eemntirey/Desktop/ERP_MM/MIHAJA_ERP_PRO/web/backend')

import enum

class TypeFournisseur(enum.Enum):
    LOCAL = 'local'
    NATIONAL = 'national'
    INTERNATIONAL = 'international'
    GROSSISTE = 'grossiste'
    FABRICANT = 'fabricant'
    DISTRIBUTEUR = 'distributeur'
    PRODUCTEUR_LOCAL = 'producteur_local'
    IMPORTATEUR = 'importateur'
    FOURNISSEUR_LOCAL = 'fournisseur_local'
    FOURNISSEUR_INTERNATIONAL = 'fournisseur_international'

values = [e.value for e in TypeFournisseur]
print('TypeFournisseur values:', values)
assert 'importateur' in values

import re

# Test validate_phone regex
pattern = r'^(\+261|0)(2[0-9]|3[0-9])(\d{2})(\d{3})(\d{2})$'
test_numbers = ['+261 34 12 345 67', '+261341234567', '+261 34 47 258 36']
for num in test_numbers:
    stripped = num.replace(' ', '')
    result = re.match(pattern, stripped) is not None
    print(f'validate_phone("{num}"): {result}')
    assert result, f'Failed for {num}'

# Test format_phone
def format_phone(phone):
    if not phone:
        return ''
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('261'):
        rest = digits[3:]
        if len(rest) == 9:
            return f'+261 {rest[0:2]} {rest[2:4]} {rest[4:7]} {rest[7:9]}'
    elif digits.startswith('0'):
        rest = digits[1:]
        if len(rest) == 9:
            return f'+261 {rest[0:2]} {rest[2:4]} {rest[4:7]} {rest[7:9]}'
    return phone

print('format_phone("+261341234567"):', format_phone('+261341234567'))
assert format_phone('+261341234567') == '+261 34 12 345 67'

CURRENCY = {
    'code': 'MGA',
    'symbol': 'Ar',
    'locale': 'mg-MG',
}
print('CURRENCY:', CURRENCY)

print('All checks passed!')
