from decimal import Decimal
import re

def validate_email(email):
    """Valide un email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Valide un numéro de téléphone malgache au format +261 XX XX XXX XX ou 0XX XX XX XXX XX"""
    pattern = r'^(\+261|0)(2[0-9]|3[0-9])(\d{2})(\d{3})(\d{2})$'
    return re.match(pattern, phone.replace(' ', '')) is not None

def format_phone(phone):
    """Formate un numéro de téléphone malgache au format international +261 XX XX XXX XX"""
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

def validate_siret(siret):
    """Valide un numéro SIRET"""
    return len(siret) == 14 and siret.isdigit()

def validate_product_data(data):
    """Valide les données d'un produit"""
    required = ['reference', 'nom', 'prix_achat_ht', 'prix_vente_ht']
    for field in required:
        if field not in data:
            raise ValueError(f"Le champ {field} est requis")
    
    if data.get('prix_achat_ht', 0) <= 0:
        raise ValueError("Le prix d'achat doit être supérieur à 0")
    
    if data.get('prix_vente_ht', 0) <= 0:
        raise ValueError("Le prix de vente doit être supérieur à 0")
    
    if data.get('taux_tva', 0) < 0:
        raise ValueError("Le taux de TVA doit être positif")
    
    if data.get('quantite_stock', 0) < 0:
        raise ValueError("La quantité en stock doit être positive")