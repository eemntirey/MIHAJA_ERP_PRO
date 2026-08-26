import sys
sys.path.insert(0, 'C:/Users/eemntirey/Desktop/ERP_MM/MIHAJA_ERP_PRO/web/backend')

from app.models.fournisseur import TypeFournisseur
values = [e.value for e in TypeFournisseur]
print('TypeFournisseur values:', values)
assert 'importateur' in values, 'IMPORTATEUR missing!'

from app.utils.validators import validate_phone, format_phone
print('validate_phone spaced:', validate_phone('+261 34 12 345 67'))
print('validate_phone compact:', validate_phone('+261341234567'))
assert validate_phone('+261 34 12 345 67'), 'validate_phone failed'
assert validate_phone('+261341234567'), 'validate_phone failed'

print('format_phone +261:', format_phone('+261341234567'))
print('format_phone 0:', format_phone('0341234567'))
assert format_phone('+261341234567') == '+261 34 12 345 67', 'format_phone failed'

from app.constants import CURRENCY
print('CURRENCY:', CURRENCY)
assert CURRENCY['code'] == 'MGA'

print('All checks passed!')
