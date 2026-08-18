from app.models.produit import Produit
from decimal import Decimal

def test_produit_model():
    produit = Produit(nom='Test', reference='TEST001', prix_vente_ht=Decimal('9.99'))
    assert produit.nom == 'Test'
    assert produit.reference == 'TEST001'
    assert produit.prix_vente_ht == Decimal('9.99')
