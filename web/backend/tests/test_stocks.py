from app.models.stock import MouvementStock, TypeMouvement
from decimal import Decimal

def test_mouvement_stock_model():
    mouvement = MouvementStock(produit_id=1, type_mouvement=TypeMouvement.ENTREE, quantite=Decimal('10.0'))
    assert mouvement.produit_id == 1
    assert mouvement.type_mouvement == TypeMouvement.ENTREE
    assert mouvement.quantite == Decimal('10.0')
